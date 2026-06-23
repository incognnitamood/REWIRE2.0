import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Beaker, Dna, ImageOff, Network as NetworkIcon } from 'lucide-react'

// Lightweight, in-browser fallback for functional groups. We deliberately avoid
// shipping a cheminformatics engine (RDKit/WASM) to the client — these are
// curated annotations for our test drugs, with a generic fallback otherwise.
const FUNCTIONAL_GROUPS = {
  lapatinib: ['amine', 'halogen', 'heterocycle'],
  imatinib: ['pyrimidine', 'amide', 'piperazine'],
  gefitinib: ['quinazoline', 'ether', 'morpholine', 'halogen'],
  erlotinib: ['quinazoline', 'alkyne', 'ether'],
  osimertinib: ['pyrimidine', 'acrylamide', 'indole'],
  nilotinib: ['pyrimidine', 'amide', 'imidazole', 'trifluoromethyl'],
  dasatinib: ['aminothiazole', 'amide', 'piperazine'],
  ponatinib: ['imidazopyridazine', 'alkyne', 'amide', 'piperazine'],
  sorafenib: ['urea', 'pyridine', 'halogen', 'amide'],
  sunitinib: ['indole', 'pyrrole', 'amide', 'amine'],
  regorafenib: ['urea', 'pyridine', 'halogen', 'amide'],
  vemurafenib: ['sulfonamide', 'halogen', 'azaindole'],
  tamoxifen: ['alkene', 'ether', 'amine', 'aromatic'],
  letrozole: ['nitrile', 'triazole', 'aromatic'],
  anastrozole: ['nitrile', 'triazole', 'aromatic'],
  methotrexate: ['pteridine', 'carboxylic acid', 'amine', 'amide'],
  donepezil: ['piperidine', 'ether', 'ketone', 'aromatic'],
  galantamine: ['amine', 'ether', 'phenol', 'alkene'],
}

const GENERIC_GROUPS = ['Targeted Inhibitor']

function groupsFor(drugName) {
  if (!drugName) return GENERIC_GROUPS
  return FUNCTIONAL_GROUPS[drugName.toLowerCase()] || GENERIC_GROUPS
}

export default function DrugChemicalProfile({ drugName, onViewNetwork }) {
  const [imgError, setImgError] = useState(false)

  // Reset the image error state whenever the selected drug changes.
  useEffect(() => {
    setImgError(false)
  }, [drugName])

  if (!drugName) return null

  const groups = groupsFor(drugName)
  const imgUrl = `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/${encodeURIComponent(
    drugName,
  )}/PNG`

  return (
    <motion.div
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 16 }}
      transition={{ duration: 0.28, ease: 'easeOut' }}
      className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
    >
      {/* Header */}
      <div className="flex items-center gap-2.5 border-b border-slate-100 px-5 py-4">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-blue-600 text-white shadow-md shadow-indigo-500/30">
          <Beaker className="h-4 w-4" strokeWidth={2.4} />
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-bold text-slate-900">{drugName}</p>
          <p className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
            Chemical Profile
          </p>
        </div>
      </div>

      {/* Feature A: 2D molecular structure */}
      <div className="px-5 pt-5">
        <div className="flex h-48 items-center justify-center rounded-xl border border-slate-200 bg-slate-50/70 p-3">
          {imgError ? (
            <div className="flex flex-col items-center gap-2 text-slate-400">
              <ImageOff className="h-7 w-7" />
              <p className="text-xs font-medium">2D structure unavailable</p>
              <p className="text-[10px] text-slate-300">Not found in PubChem</p>
            </div>
          ) : (
            <img
              src={imgUrl}
              alt={`2D structure of ${drugName}`}
              loading="lazy"
              onError={() => setImgError(true)}
              className="max-h-full max-w-full object-contain mix-blend-multiply"
            />
          )}
        </div>
        <p className="mt-1.5 text-center text-[10px] text-slate-400">
          Source: PubChem PUG REST
        </p>
      </div>

      {/* Feature B: Chemical composition */}
      <div className="px-5 pb-5 pt-4">
        <div className="mb-2.5 flex items-center gap-2">
          <Dna className="h-4 w-4 text-indigo-500" strokeWidth={2.4} />
          <h4 className="text-sm font-bold text-slate-800">Chemical Composition</h4>
        </div>
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Functional Groups
        </p>
        <div className="flex flex-wrap gap-2">
          {groups.map((g) => (
            <span
              key={g}
              className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium capitalize text-slate-700 ring-1 ring-inset ring-slate-200/80 transition-colors hover:bg-indigo-50 hover:text-indigo-700"
            >
              {g}
            </span>
          ))}
        </div>

        {onViewNetwork && (
          <button
            onClick={onViewNetwork}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition-colors hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700"
          >
            <NetworkIcon className="h-4 w-4" />
            View Network Topology
          </button>
        )}
      </div>
    </motion.div>
  )
}
