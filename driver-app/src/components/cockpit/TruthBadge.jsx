import TruthLabel from '../TruthLabel.jsx'

/** Compact truth chip for cockpit surfaces */
export default function TruthBadge(props) {
  return <TruthLabel {...props} className={`text-[10px] normal-case tracking-normal ${props.className || ''}`} />
}
