import { lazy, Suspense, useEffect, useState } from 'react'
import { Link, NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { ChartNoAxesCombined, FlaskConical, Menu, Moon, ScanSearch, Sun, X } from 'lucide-react'
import { motion, AnimatePresence } from 'motion/react'
import { Button } from '../components/ui/button'
import { LoadingState } from '../components/ui/states'
import { Overview } from './Overview'

const Studio = lazy(() => import('./Studio').then(module => ({ default: module.Studio })))
const AutomaticAnalysis = lazy(() => import('./AutomaticAnalysis').then(module => ({ default: module.AutomaticAnalysis })))
const StandaloneAnalysis = lazy(() => import('./StandaloneAnalysis').then(module => ({ default: module.StandaloneAnalysis })))
const StandaloneResults = lazy(() => import('./StandaloneAnalysis').then(module => ({ default: module.StandaloneResults })))
const ManualC1Validation = lazy(() => import('./ManualC1Validation').then(module => ({ default: module.ManualC1Validation })))
const ScenarioV2 = lazy(() => import('./ScenarioV2').then(module => ({ default: module.ScenarioV2 })))
const ModelValidation = lazy(() => import('./ModelValidation').then(module => ({ default: module.ModelValidation })))
const FoodPrices = lazy(() => import('./FoodPrices').then(module => ({ default: module.FoodPrices })))
const AlgorithmComparison = lazy(() => import('./AlgorithmComparison').then(module => ({ default: module.AlgorithmComparison })))
const EvidenceStatus = lazy(() => import('./EvidenceStatus').then(module => ({ default: module.EvidenceStatus })))

const links = [
  { path: '/', label: 'Overview', icon: ChartNoAxesCombined },
  { path: '/analysis', label: 'Intervention Analysis', icon: ScanSearch },
]

function ThemeButton() {
  const [theme, setTheme] = useState<'dark' | 'light'>(() => localStorage.getItem('c2-theme') === 'dark' ? 'dark' : 'light')
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem('c2-theme', theme) }, [theme])
  return <Button variant="ghost" aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`} onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} className="!px-3">{theme === 'dark' ? <Sun size={19}/> : <Moon size={19}/>}</Button>
}

function NavItems({ close }: { close: () => void }) {
  return <nav aria-label="Main navigation" className="space-y-1.5">
    {links.map(({ path, label, icon: Icon }) => <NavLink key={path} to={path} onClick={close} end className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}>
      <Icon size={18} aria-hidden="true" /><span>{label}</span>
    </NavLink>)}
  </nav>
}

function NotFound() {
  const location = useLocation()
  return <div className="panel p-8"><h1 className="text-2xl font-semibold">Page unavailable</h1><p className="mt-2 text-[var(--muted)]">No workspace exists at {location.pathname}.</p><Link className="text-link mt-4 inline-block" to="/">Return to overview</Link></div>
}

export function App() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()
  useEffect(() => { setMobileOpen(false) }, [location.pathname])
  return <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
    <aside className="sidebar fixed inset-y-0 left-0 z-30 hidden w-68 flex-col border-r border-[var(--line)] px-5 py-7 lg:flex">
      <Link to="/" className="mb-11 flex items-center gap-3"><div className="flex size-11 items-center justify-center rounded-2xl bg-cyan-400 text-slate-950"><FlaskConical size={23}/></div><div><strong className="block text-lg tracking-tight">FedNutri<span className="text-cyan-400">-XAI</span></strong><span className="text-xs uppercase tracking-[.2em] text-[var(--muted)]">Component 02</span></div></Link>
      <span className="mb-4 px-3 text-[11px] font-semibold uppercase tracking-[.23em] text-[var(--muted)]">Research workspace</span><NavItems close={() => {}} />
    </aside>
    <div className="lg:pl-68">
      <header className="sticky top-0 z-20 flex h-18 items-center justify-between border-b border-[var(--line)] bg-[var(--header)] px-5 backdrop-blur-xl md:px-9">
        <div className="flex items-center gap-3"><Button variant="ghost" className="!px-2 lg:hidden" aria-label="Open navigation" onClick={() => setMobileOpen(true)}><Menu size={22}/></Button><div><span className="text-xs text-[var(--muted)]">FedNutri-XAI / Component 2</span><h2 className="text-sm font-semibold md:text-base">Personalized Counterfactual Intervention Engine</h2></div></div>
        <div className="flex items-center gap-2"><span className="hidden items-center gap-2 rounded-full border border-cyan-400/20 px-3 py-1.5 text-xs text-cyan-300 sm:inline-flex"><span className="size-1.5 rounded-full bg-cyan-400"/>Research prototype</span><ThemeButton/></div>
      </header>
      <main className="mx-auto max-w-[1660px] px-5 py-7 md:px-9 md:py-9"><Suspense fallback={<LoadingState label="Opening research workspace…"/>}><Routes><Route path="/" element={<Overview/>}/><Route path="/analysis" element={<ScenarioV2/>}/><Route path="/analysis/results" element={<StandaloneResults/>}/><Route path="/manual-c1" element={<Navigate to="/analysis" replace/>}/><Route path="/legacy-c1-comparison" element={<ManualC1Validation/>}/><Route path="/research-test" element={<StandaloneAnalysis/>}/><Route path="/c1-comparison" element={<AutomaticAnalysis/>}/><Route path="/studio" element={<Studio/>}/><Route path="/advanced-testing" element={<Studio/>}/><Route path="/model-validation" element={<ModelValidation/>}/><Route path="/algorithm-comparison" element={<AlgorithmComparison/>}/><Route path="/food-price-explorer" element={<FoodPrices/>}/><Route path="/evidence-status" element={<EvidenceStatus/>}/><Route path="*" element={<NotFound/>}/></Routes></Suspense></main>
    </div>
    <AnimatePresence>{mobileOpen && <motion.div className="fixed inset-0 z-50 lg:hidden" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <button aria-label="Close navigation overlay" className="absolute inset-0 bg-slate-950/75" onClick={() => setMobileOpen(false)}/>
      <motion.aside initial={{ x: -280 }} animate={{ x: 0 }} exit={{ x: -280 }} transition={{ duration: .2 }} className="sidebar absolute inset-y-0 left-0 w-[min(85vw,320px)] border-r border-[var(--line)] p-5 shadow-2xl">
        <div className="mb-8 flex items-center justify-between"><strong className="text-lg">FedNutri<span className="text-cyan-400">-XAI</span></strong><Button variant="ghost" aria-label="Close navigation" onClick={() => setMobileOpen(false)}><X size={20}/></Button></div><NavItems close={() => setMobileOpen(false)}/><p className="mt-8 text-xs text-[var(--muted)]">Component 2 · Research test mode</p>
      </motion.aside>
    </motion.div>}</AnimatePresence>
  </div>
}
