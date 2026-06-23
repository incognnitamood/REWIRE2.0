import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

// Conditional className helper with Tailwind conflict resolution.
export function cn(...inputs) {
  return twMerge(clsx(inputs))
}

// Disease cluster taxonomy. `key` matches the backend's exact disease string;
// `label` is the human-friendly display name.
export const DISEASE_GROUPS = [
  {
    category: 'Neurological',
    icon: 'Brain',
    accent: 'violet',
    diseases: [
      { key: 'Alzheimers', label: "Alzheimer's" },
      { key: 'Parkinsons', label: "Parkinson's" },
    ],
  },
  {
    category: 'Oncology',
    icon: 'Microscope',
    accent: 'rose',
    diseases: [
      { key: 'Breast_Cancer', label: 'Breast Cancer' },
      { key: 'Leukemia', label: 'Leukemia' },
    ],
  },
  {
    category: 'Metabolic / Cardio',
    icon: 'Activity',
    accent: 'emerald',
    diseases: [
      { key: 'Type2_Diabetes', label: 'Type 2 Diabetes' },
      { key: 'Hypertension', label: 'Hypertension' },
    ],
  },
  {
    category: 'Autoimmune',
    icon: 'Shield',
    accent: 'amber',
    diseases: [
      { key: 'Rheumatoid_Arthritis', label: 'Rheumatoid Arthritis' },
      { key: "Crohns", label: "Crohn's Disease" },
    ],
  },
]

// Flat lookup: backend key -> friendly label.
export const DISEASE_LABELS = DISEASE_GROUPS.reduce((acc, g) => {
  g.diseases.forEach((d) => (acc[d.key] = d.label))
  return acc
}, {})

export const labelFor = (key) => DISEASE_LABELS[key] || key
