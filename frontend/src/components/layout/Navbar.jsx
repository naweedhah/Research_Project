import { PageHeader } from '../../ui';

/* Component 4's pages render <Navbar title subtitle />; in the integrated app the shell provides the top bar, so this
   only draws the page header in the shared style. */
export default function Navbar({ title = 'Dashboard', subtitle }) {
  return <PageHeader component="c4" title={title} subtitle={subtitle} />;
}
