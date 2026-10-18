import { useRef, useState } from 'react';
import { Camera, User } from 'lucide-react';
import toast from 'react-hot-toast';
import Navbar from '../components/layout/Navbar';
import { useApp } from '../context/AppContext';

export default function Profile() {
  const { profile, updateProfile } = useApp();
  const [form, setForm] = useState(profile);
  const fileRef = useRef(null);

  const onPhoto = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setForm((f) => ({ ...f, avatar: reader.result }));
    reader.readAsDataURL(file);
  };

  return (
    <div className="min-h-screen">
      <Navbar title="Profile" subtitle="Manage your identity for reports and audits" />
      <div className="mx-auto max-w-2xl p-4 md:p-6">
        <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
          <div className="mb-6 flex items-center gap-4">
            <div className="relative">
              <div className="flex h-20 w-20 items-center justify-center overflow-hidden rounded-2xl bg-primary text-white">
                {form.avatar ? (
                  <img src={form.avatar} alt="" className="h-full w-full object-cover" />
                ) : (
                  <User size={32} />
                )}
              </div>
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                className="absolute -bottom-1 -right-1 rounded-full bg-secondary p-2 text-white shadow"
              >
                <Camera size={14} />
              </button>
              <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onPhoto} />
            </div>
            <div>
              <h3 className="text-xl font-bold text-primary">{form.name}</h3>
              <p className="text-sm text-slate-500">{form.role}</p>
            </div>
          </div>

          <div className="space-y-3">
            {['name', 'role', 'email', 'organization'].map((field) => (
              <div key={field}>
                <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                  {field}
                </label>
                <input
                  value={form[field] || ''}
                  onChange={(e) => setForm({ ...form, [field]: e.target.value })}
                  className="w-full rounded-xl border border-slate-200 bg-surface px-3 py-2.5 text-sm outline-none focus:border-secondary"
                />
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={() => {
              updateProfile(form);
              toast.success('Profile updated');
            }}
            className="mt-6 w-full rounded-full bg-secondary py-3 text-sm font-semibold text-white"
          >
            Save changes
          </button>
        </div>
      </div>
    </div>
  );
}
