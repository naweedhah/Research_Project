import { useState } from 'react';
import toast from 'react-hot-toast';
import Navbar from '../components/layout/Navbar';
import { useApp } from '../context/AppContext';

export default function Settings() {
  const { profile, updateProfile } = useApp();
  const [userForm, setUserForm] = useState(profile);

  return (
    <div className="min-h-screen">
      <Navbar
        title="Settings"
        subtitle="Account preferences for the decision-support workspace"
      />
      <div className="max-w-2xl space-y-5 p-4 md:p-6">
        <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
          <h3 className="text-xl font-bold text-primary">User settings</h3>
          <p className="mb-5 text-base text-slate-500">
            Display identity used across the dashboard
          </p>
          {['name', 'role', 'email', 'organization'].map((field) => (
            <div key={field} className="mb-3">
              <label className="mb-1.5 block text-sm font-semibold uppercase tracking-wide text-slate-500">
                {field === 'name' ? 'Full name' : field}
              </label>
              <input
                value={userForm[field] || ''}
                onChange={(e) => setUserForm({ ...userForm, [field]: e.target.value })}
                className="w-full rounded-xl border border-slate-200 bg-surface px-3 py-2.5 text-base outline-none focus:border-secondary"
              />
            </div>
          ))}
          <button
            type="button"
            onClick={() => {
              updateProfile(userForm);
              toast.success('User settings saved');
            }}
            className="mt-2 w-full rounded-full bg-gradient-to-r from-secondary to-[#4C6EF5] py-3 text-base font-semibold text-white"
          >
            Save changes
          </button>
        </div>

        <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
          <h3 className="text-xl font-bold text-primary">Research note</h3>
          <p className="mt-2 text-base leading-relaxed text-slate-600">
            Forecast horizons (H1, H3, H6) and research model outputs are produced
            automatically by the backend. Doctors select only district, year and
            month. There is no model or horizon configuration in this interface.
          </p>
        </div>
      </div>
    </div>
  );
}
