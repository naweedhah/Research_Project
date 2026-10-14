"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Loader2, X } from "lucide-react";
import { api } from "@/services/component4/httpClient";
import { Button } from "@/components/common/button";
import { Input, Label, Select } from "@/components/common/field";
import { ageLabel } from "@/utils/utils";
import type { ChildProfile } from "@/data/child-profile";
import { toast } from "sonner";

type RegistrationOptions = {
  facility: { id: string; name: string | null; code: string | null; district: string | null };
  care_teams: string[];
  caregiver_relationships: string[];
  districts: string[];
  moh_areas: string[];
  doctors: { id: string; full_name: string; email: string }[];
  current_user_id: string;
};

const fieldClass =
  "border-[#e8eef5] focus:border-[#2563eb] focus:outline-none focus:ring-2 focus:ring-[#2563eb]/20";

function ageFromDob(dob: string): string {
  if (!dob) return "—";
  const birth = new Date(dob);
  const today = new Date();
  let months = (today.getFullYear() - birth.getFullYear()) * 12 + (today.getMonth() - birth.getMonth());
  if (today.getDate() < birth.getDate()) months -= 1;
  return ageLabel(Math.max(0, months));
}

type RegisterChildModalProps = {
  open: boolean;
  onClose: () => void;
  editChildId?: string | null;
};

export function RegisterChildModal({ open, onClose, editChildId = null }: RegisterChildModalProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [dob, setDob] = useState("");
  const [district, setDistrict] = useState("");

  const options = useQuery({
    queryKey: ["registration-options"],
    queryFn: () => api<RegistrationOptions>("/children/registration-options"),
    enabled: open,
  });
  const existing = useQuery({
    queryKey: ["child", editChildId],
    queryFn: () => api<ChildProfile>(`/children/${editChildId}`),
    enabled: open && Boolean(editChildId),
  });

  useEffect(() => {
    if (!open) return;
    setError(null);
    if (!editChildId) {
      setDob("");
      setDistrict("");
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose, editChildId]);

  useEffect(() => {
    if (!open || !editChildId || !existing.data) return;
    setDob(existing.data.date_of_birth?.slice(0, 10) ?? "");
    setDistrict(existing.data.district ?? "");
  }, [open, editChildId, existing.data]);

  useEffect(() => {
    if (editChildId) return;
    if (options.data?.facility.district && !district) {
      setDistrict(options.data.facility.district);
    }
  }, [options.data, district, editChildId]);

  const mohAreas = useMemo(() => {
    if (!options.data) return [];
    if (district && district !== options.data.facility.district) {
      return options.data.districts.includes(district) ? [`${district} MOH — configure`] : options.data.moh_areas;
    }
    return options.data.moh_areas;
  }, [options.data, district]);

  if (!open) return null;

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setSaving(true);
    setError(null);
    try {
      const payload = {
        full_name: form.get("full_name"),
        date_of_birth: form.get("dob"),
        sex: form.get("sex"),
        external_patient_id: form.get("external"),
        responsible_team: form.get("team"),
        assigned_doctor_id: form.get("doctor") || options.data?.current_user_id,
        district: form.get("district") || null,
        moh_area: form.get("moh") || null,
        phm_area: form.get("phm") || null,
        caregiver_relationship: form.get("rel"),
        caregiver_display_name: form.get("caregiver") || null,
        caregiver_phone: form.get("phone") || null,
        reminder_consent: form.get("reminder") === "on",
      };
      if (editChildId) {
        await api(`/children/${editChildId}`, { method: "PATCH", body: JSON.stringify(payload) });
        await queryClient.invalidateQueries({ queryKey: ["children"] });
        await queryClient.invalidateQueries({ queryKey: ["child", editChildId] });
        toast.success("Child record updated.");
        onClose();
        return;
      }
      const created = await api<{ id: string; pseudonymous_id: string; message: string }>("/children", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      await queryClient.invalidateQueries({ queryKey: ["children"] });
      toast.success(created.message);
      onClose();
      router.push(`/children/${created.id}?registered=1`);
    } catch (err) {
      setError(err instanceof Error ? err.message : editChildId ? "Unable to save this child record" : "Unable to register child");
    } finally {
      setSaving(false);
    }
  }

  const facilityName = options.data?.facility.name ?? "Your facility";
  const record = editChildId ? existing.data : null;
  const teams = options.data?.care_teams ?? [];
  const teamOptions = record?.responsible_team && !teams.includes(record.responsible_team) ? [record.responsible_team, ...teams] : teams;
  const relationships = options.data?.caregiver_relationships ?? ["Mother"];
  const relationship = record?.caregiver?.relationship;
  const relationshipOptions = relationship && !relationships.includes(relationship) ? [relationship, ...relationships] : relationships;
  const districts = options.data?.districts ?? [];
  const districtOptions = record?.district && !districts.includes(record.district) ? [record.district, ...districts] : districts;
  const mohOptions = record?.moh_area && !mohAreas.includes(record.moh_area) ? [record.moh_area, ...mohAreas] : mohAreas;

  return (
    <div className="fixed inset-0 z-40 overflow-y-auto">
      <div className="absolute inset-0 bg-[#0A2748]/40 backdrop-blur-md" aria-hidden />
      <div className="relative flex min-h-full items-start justify-center px-4 py-10 sm:items-center sm:px-6 sm:py-12">
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="register-child-title"
          className="relative w-full max-w-3xl"
        >
          <button
            type="button"
            onClick={onClose}
            className="absolute right-3 top-3 z-10 rounded-lg p-2 text-[#64748b] hover:bg-white hover:text-[#0A2748]"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>

          <div className="overflow-hidden rounded-2xl border border-[#e4ecf4] bg-white shadow-[0_24px_64px_-28px_rgba(10,39,72,0.45)]">
            <div className="border-b border-[#e4ecf4] bg-[#f7f9fc] px-6 py-5 pr-14">
              <h2 id="register-child-title" className="text-2xl font-bold text-[#0f2744]">
                {editChildId ? "Edit child record" : "Register new child"}
              </h2>
              <p className="mt-1 text-sm text-[#64748b]">
                Facility: {facilityName}
                {options.data?.facility.code ? ` · ${options.data.facility.code}` : ""}
              </p>
            </div>

            <form key={editChildId ? `${editChildId}-${existing.dataUpdatedAt}` : "register"} onSubmit={onSubmit}>
              <div className="max-h-[min(70vh,36rem)] overflow-y-auto px-6 pb-6 pt-5">
                <div className="space-y-4">
                  {options.isLoading || (editChildId && existing.isLoading) ? (
                    <p className="py-8 text-center text-sm text-[#64748b]">Loading registration options…</p>
                  ) : (
                    <>
                      <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#94a3b8]">Patient information</p>
                      <div>
                        <Label htmlFor="reg-external">
                          Hospital / Patient ID <span className="text-clinical-danger">*</span>
                        </Label>
                        <Input id="reg-external" name="external" required defaultValue={record?.external_patient_id ?? ""} className={fieldClass} />
                      </div>
                      <div>
                        <Label htmlFor="reg-name">
                          Child full name <span className="text-clinical-danger">*</span>
                        </Label>
                        <Input id="reg-name" name="full_name" required minLength={2} defaultValue={record?.full_name ?? ""} className={fieldClass} />
                      </div>
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div>
                          <Label htmlFor="reg-dob">
                            Date of birth <span className="text-clinical-danger">*</span>
                          </Label>
                          <Input
                            id="reg-dob"
                            name="dob"
                            type="date"
                            required
                            max={new Date().toISOString().slice(0, 10)}
                            value={dob}
                            onChange={(e) => setDob(e.target.value)}
                            className={fieldClass}
                          />
                        </div>
                        <div>
                          <Label>Age</Label>
                          <Input readOnly disabled value={ageFromDob(dob)} className="border-[#e8eef5] bg-[#f8fafc] text-[#0f2744]" />
                        </div>
                      </div>
                      <div>
                        <Label htmlFor="reg-sex">
                          Sex <span className="text-clinical-danger">*</span>
                        </Label>
                        <Select id="reg-sex" name="sex" required defaultValue={record?.sex || "female"} className={fieldClass}>
                          <option value="female">Female</option>
                          <option value="male">Male</option>
                        </Select>
                      </div>

                      <div className="border-t border-[#e4ecf4] pt-4">
                        <p className="mb-3 text-[11px] font-medium uppercase tracking-[0.08em] text-[#94a3b8]">Care assignment</p>
                        <div className="space-y-4">
                          <div>
                            <Label>Facility</Label>
                            <Input readOnly disabled value={facilityName} className="border-[#e8eef5] bg-[#f8fafc]" />
                          </div>
                          <div className="grid gap-3 sm:grid-cols-2">
                            <div>
                              <Label htmlFor="reg-team">
                                Clinic / care team <span className="text-clinical-danger">*</span>
                              </Label>
                              <Select id="reg-team" name="team" required defaultValue={record?.responsible_team ?? ""} className={fieldClass}>
                                <option value="">Select…</option>
                                {teamOptions.map((t) => (
                                  <option key={t} value={t}>
                                    {t}
                                  </option>
                                ))}
                              </Select>
                            </div>
                            <div>
                              <Label htmlFor="reg-doctor">Assigned doctor</Label>
                              <Select id="reg-doctor" name="doctor" defaultValue={record?.assigned_doctor?.id ?? options.data?.current_user_id} className={fieldClass}>
                                {(options.data?.doctors ?? []).map((d) => (
                                  <option key={d.id} value={d.id}>
                                    {d.full_name}
                                  </option>
                                ))}
                              </Select>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="border-t border-[#e4ecf4] pt-4">
                        <p className="mb-3 text-[11px] font-medium uppercase tracking-[0.08em] text-[#94a3b8]">Primary caregiver</p>
                        <div className="space-y-4">
                          <div>
                            <Label htmlFor="reg-caregiver">Caregiver name</Label>
                            <Input id="reg-caregiver" name="caregiver" defaultValue={record?.caregiver?.display_name ?? ""} className={fieldClass} />
                          </div>
                          <div className="grid gap-3 sm:grid-cols-2">
                            <div>
                              <Label htmlFor="reg-rel">
                                Relationship <span className="text-clinical-danger">*</span>
                              </Label>
                              <Select id="reg-rel" name="rel" required defaultValue={relationship || "Mother"} className={fieldClass}>
                                {relationshipOptions.map((r) => (
                                  <option key={r} value={r}>
                                    {r}
                                  </option>
                                ))}
                              </Select>
                            </div>
                            <div>
                              <Label htmlFor="reg-phone">Contact number</Label>
                              <Input id="reg-phone" name="phone" type="tel" defaultValue={record?.caregiver?.phone ?? ""} className={fieldClass} />
                            </div>
                          </div>
                          <label className="flex items-center gap-2 text-sm">
                            <input type="checkbox" name="reminder" defaultChecked={Boolean(record?.caregiver?.reminder_consent)} />
                            Allow clinic appointment / follow-up reminders
                          </label>
                        </div>
                      </div>

                      <div className="border-t border-[#e4ecf4] pt-4">
                        <p className="mb-3 text-[11px] font-medium uppercase tracking-[0.08em] text-[#94a3b8]">Location</p>
                        <div className="space-y-4">
                          <div className="grid gap-3 sm:grid-cols-2">
                            <div>
                              <Label htmlFor="reg-district">District</Label>
                              <Select id="reg-district" name="district" value={district} onChange={(e) => setDistrict(e.target.value)} className={fieldClass}>
                                <option value="">Select…</option>
                                {districtOptions.map((d) => (
                                  <option key={d} value={d}>
                                    {d}
                                  </option>
                                ))}
                              </Select>
                            </div>
                            <div>
                              <Label htmlFor="reg-moh">MOH area</Label>
                              <Select id="reg-moh" name="moh" defaultValue={record?.moh_area ?? ""} className={fieldClass}>
                                <option value="">Select…</option>
                                {mohOptions.map((m) => (
                                  <option key={m} value={m}>
                                    {m}
                                  </option>
                                ))}
                              </Select>
                            </div>
                          </div>
                          <div>
                            <Label htmlFor="reg-phm">PHM area (optional)</Label>
                            <Input id="reg-phm" name="phm" defaultValue={record?.phm_area ?? ""} className={fieldClass} />
                          </div>
                        </div>
                      </div>
                    </>
                  )}

                  {error ? (
                    <p className="text-sm text-clinical-danger">
                      {editChildId ? "Unable to save this child record." : "Unable to register child. Your entered information has not been lost."} {error}
                    </p>
                  ) : null}

                  <div className="flex justify-between pt-2">
                    <Button type="button" variant="secondary" onClick={onClose}>
                      Cancel
                    </Button>
                    <Button type="submit" disabled={saving || options.isLoading || (Boolean(editChildId) && existing.isLoading)}>
                      {saving ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          {editChildId ? "Saving…" : "Registering…"}
                        </>
                      ) : editChildId ? (
                        "Save changes"
                      ) : (
                        <>
                          Register child
                          <ArrowRight className="h-4 w-4" />
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
