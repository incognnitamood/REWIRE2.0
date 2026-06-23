"""REWIRE — Graph Attention Network for drug repurposing embeddings.

``RepurposingGAT`` learns a 16-dimensional embedding for each drug.  A drug is
grounded in the PPI network through its *target genes*: the model runs graph
attention over the whole PPI graph to produce node embeddings, mean-pools the
embeddings of the drug's target nodes (``global_mean_pool``), and fuses the
drug's Rewiring Sensitivity Vector (RSV) into the final representation.

Training (see train_gat.py) pulls drugs that treat the same disease together and
pushes different-disease drugs apart with a cosine-embedding objective, so the
learned space groups mechanistically/therapeutically related drugs.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATConv, global_mean_pool

HIDDEN_DIM = 16
DROPOUT = 0.5
HEADS = 4


class RepurposingGAT(nn.Module):
    """GAT over the PPI graph + RSV fusion -> per-drug embedding.

    Args:
        in_dim:   number of input node features on the PPI graph.
        hidden_dim: embedding width (default 16).
        rsv_dim:  dimensionality of the per-drug RSV vector (default 4).
        heads:    attention heads in the first GAT layer.
        dropout:  dropout probability (default 0.5), applied to features and to
                  the attention coefficients inside GATConv.
    """

    def __init__(self, in_dim, hidden_dim=HIDDEN_DIM, rsv_dim=4,
                 heads=HEADS, dropout=DROPOUT):
        super().__init__()
        self.dropout = dropout

        # Two attention layers: the first is multi-head (concatenated), the
        # second collapses to a single head producing the node embedding.
        self.conv1 = GATConv(in_dim, hidden_dim, heads=heads, dropout=dropout)
        self.conv2 = GATConv(hidden_dim * heads, hidden_dim, heads=1,
                             concat=False, dropout=dropout)

        # Fuse the pooled structural embedding with the drug's RSV signature.
        self.fuse = nn.Linear(hidden_dim + rsv_dim, hidden_dim)

    def encode_nodes(self, x, edge_index):
        """Run graph attention over the PPI graph -> node embeddings."""
        h = F.elu(self.conv1(x, edge_index))
        h = F.dropout(h, p=self.dropout, training=self.training)
        h = self.conv2(h, edge_index)
        return h

    def forward(self, x, edge_index, target_index, target_batch, rsv):
        """Compute one embedding per drug.

        Args:
            x:            node feature matrix, shape (num_nodes, in_dim).
            edge_index:   PPI connectivity, shape (2, num_edges).
            target_index: flat tensor of PPI node ids for every drug-target,
                          concatenated across drugs.
            target_batch: same length as ``target_index``; maps each target
                          node to its drug index (0 .. num_drugs-1).
            rsv:          per-drug RSV features, shape (num_drugs, rsv_dim).

        Returns:
            Tensor of shape (num_drugs, hidden_dim): the drug embeddings.
        """
        h = self.encode_nodes(x, edge_index)

        # Pool each drug's target-node embeddings into a single vector.
        pooled = global_mean_pool(h[target_index], target_batch,
                                  size=rsv.size(0))

        z = torch.cat([pooled, rsv], dim=1)
        z = self.fuse(z)
        return z


if __name__ == "__main__":
    # Tiny smoke test on a random graph.
    torch.manual_seed(0)
    n_nodes, n_drugs = 20, 4
    x = torch.randn(n_nodes, 2)
    edge_index = torch.randint(0, n_nodes, (2, 60))
    target_index = torch.randint(0, n_nodes, (n_drugs * 2,))
    target_batch = torch.arange(n_drugs).repeat_interleave(2)
    rsv = torch.randn(n_drugs, 4)

    model = RepurposingGAT(in_dim=2)
    z = model(x, edge_index, target_index, target_batch, rsv)
    print("embedding shape:", tuple(z.shape))  # (4, 16)
