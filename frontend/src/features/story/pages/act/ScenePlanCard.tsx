import { useState, type ReactNode } from "react";
import type { Place, PlaceDraft, ScenePlan } from "@/features/story/model/types";
import { cn } from "@/shared/lib/utils";
import { Chip } from "@/shared/ui/Chip";
import { SerifInput } from "@/shared/ui/fields/SerifInput";
import { TextField } from "@/shared/ui/fields/TextField";
import { HeaderPill } from "@/shared/ui/HeaderPill";
import { Notice } from "@/shared/ui/Notice";

export interface CastChip {
  id: string;
  label: string;
}

interface ScenePlanCardProps {
  number: number;
  plan: ScenePlan;
  places: Place[];
  cast: CastChip[];
  onChange(patch: Partial<ScenePlan>): void;
  onCreatePlace(draft: PlaceDraft): Promise<Place | null>;
  /** Status, APPROVE / REOPEN on the right of the place (plans), or nothing (an open structure scene). */
  status?: { label: string; approved: boolean; busy: boolean; onApprove(): void; onReopen(): void };
  /** The act's text is approved: the scene is final, shown without APPROVE / REOPEN and not editable. */
  final?: boolean;
  /** Move / cut buttons of a structure scene. */
  tools?: ReactNode;
  highlighted?: boolean;
  notice?: string;
  readOnly?: boolean;
}

/** A scene with every plan field editable: place, notes for this scene, who is on stage, what happens. */
export function ScenePlanCard({
  number,
  plan,
  places,
  cast,
  onChange,
  onCreatePlace,
  status,
  tools,
  highlighted = false,
  notice,
  readOnly: readOnlyProp = false,
  final = false,
}: ScenePlanCardProps) {
  const readOnly = readOnlyProp || final;
  const [newPlace, setNewPlace] = useState<PlaceDraft | null>(null);
  const [creating, setCreating] = useState(false);
  const place = places.find((p) => p.id === plan.place_id);

  const createPlace = async () => {
    if (!newPlace?.name.trim()) return;
    setCreating(true);
    const created = await onCreatePlace({
      name: newPlace.name.trim(),
      description: newPlace.description.trim(),
      significance: newPlace.significance.trim(),
    });
    setCreating(false);
    if (!created) return false;
    onChange({ place_id: created.id });
    setNewPlace(null);
    return true;
  };

  const approve = async () => {
    // a new place that is described but not created yet is created first
    if (newPlace?.name.trim() && !(await createPlace())) return;
    status?.onApprove();
  };

  return (
    <article
      className={cn(
        "relative grid animate-fade-up grid-cols-[44px_minmax(0,1fr)] gap-x-4 rounded-[10px] border border-line bg-card py-[18px] pr-5 pl-4",
        "transition-[border-color,background-color,box-shadow] duration-200 hover:border-line-hover focus-within:border-gold focus-within:bg-card-focus",
        status?.approved && "border-gold/50",
        highlighted && "border-gold shadow-[0_0_0_1px_#c9a24b,0_0_24px_#c9a24b44] hover:border-gold",
        tools && "grid-cols-[44px_minmax(0,1fr)_auto]",
      )}
    >
      <div aria-hidden className="pt-[2px] text-center font-serif text-[32px] leading-none text-gold italic">
        {number}
      </div>
      <div className="min-w-0">
        <div className="mb-[14px] flex items-center gap-3">
          <span className="font-serif text-[22px] leading-[1.1] font-medium">
            {newPlace ? newPlace.name.trim() || "New place" : place?.name || "No place yet"}
          </span>
          {status && (
            <>
              <span className={cn("ml-auto font-sans text-[10px] tracking-[1.5px]", status.approved ? "text-gold" : "text-muted-2")}>
                {status.label}
              </span>
              {!final && (
                <HeaderPill
                  small
                  ghost={status.approved}
                  disabled={status.busy || creating || readOnly}
                  aria-label={`${status.approved ? "Reopen" : "Approve"} scene ${number}`}
                  onClick={status.approved ? status.onReopen : () => void approve()}
                >
                  {status.approved ? "REOPEN" : "APPROVE"}
                </HeaderPill>
              )}
            </>
          )}
        </div>

        <div className="grid grid-cols-2 gap-x-6 gap-y-4">
          <Field label="PLACE">
            <div className="flex flex-wrap items-center gap-2" role="group" aria-label={`Place of scene ${number}`}>
              {places.map((p) => (
                <Chip
                  key={p.id}
                  selected={!newPlace && plan.place_id === p.id}
                  disabled={readOnly}
                  title={p.description || undefined}
                  onClick={() => {
                    setNewPlace(null);
                    onChange({ place_id: p.id });
                  }}
                  className="px-3 py-1 font-serif text-base tracking-normal"
                >
                  {p.name}
                </Chip>
              ))}
              <Chip
                selected={!!newPlace}
                disabled={readOnly}
                onClick={() => setNewPlace(newPlace ? null : { name: "", description: "", significance: "" })}
                className="border-dashed px-3 py-1 font-serif text-base tracking-normal"
              >
                + New place
              </Chip>
            </div>
          </Field>

          {newPlace && (
            <div className="col-span-2 flex animate-fade-up flex-col gap-[10px] rounded-[10px] border border-dashed border-line-strong px-4 py-[14px]">
              <span className="font-sans text-xs text-muted italic">Describe the new place, or ask the agent in the chat to create it.</span>
              <SerifInput
                aria-label="New place name"
                placeholder="Name, e.g. The boathouse"
                value={newPlace.name}
                onChange={(e) => setNewPlace({ ...newPlace, name: e.target.value })}
                className="border-b border-dotted border-line-strong pb-1 focus:border-gold"
              />
              <span className="font-sans text-[10px] tracking-[1.5px] text-muted-2">DESCRIPTION</span>
              <TextField
                lined
                rows={2}
                label="New place description"
                placeholder="What it looks like and what is in it: doors, windows, furniture, objects, atmosphere"
                value={newPlace.description}
                onChange={(description) => setNewPlace({ ...newPlace, description })}
              />
              <span className="font-sans text-[10px] tracking-[1.5px] text-muted-2">SIGNIFICANCE FOR THE STORY</span>
              <TextField
                lined
                rows={1}
                label="Significance for the story"
                placeholder="e.g. The house everyone wants to inherit"
                value={newPlace.significance}
                onChange={(significance) => setNewPlace({ ...newPlace, significance })}
              />
              <div className="flex justify-end">
                <HeaderPill small disabled={!newPlace.name.trim() || creating} onClick={() => void createPlace()}>
                  CREATE PLACE
                </HeaderPill>
              </div>
            </div>
          )}

          <Field label="PLACE NOTES · IN THIS SCENE">
            <TextField
              lined
              rows={1}
              label="Place notes"
              placeholder="e.g. The lights are out"
              value={plan.place_notes}
              readOnly={readOnly}
              onChange={(place_notes) => onChange({ place_notes })}
            />
          </Field>
          <Field label="ON STAGE">
            <div className="flex flex-wrap gap-[6px]" role="group" aria-label={`Characters on stage in scene ${number}`}>
              {cast.map((c) => {
                const on = plan.character_ids.includes(c.id);
                return (
                  <Chip
                    key={c.id}
                    selected={on}
                    disabled={readOnly}
                    onClick={() =>
                      onChange({ character_ids: on ? plan.character_ids.filter((id) => id !== c.id) : [...plan.character_ids, c.id] })
                    }
                  >
                    {c.label}
                  </Chip>
                );
              })}
            </div>
          </Field>
          <Field label="WHAT HAPPENS">
            <TextField
              lined
              rows={2}
              label="What happens"
              value={plan.what_happens}
              readOnly={readOnly}
              onChange={(what_happens) => onChange({ what_happens })}
            />
          </Field>
        </div>
        {notice && <Notice className="mt-4">{notice}</Notice>}
      </div>
      {tools && <div className="flex items-start gap-[6px]">{tools}</div>}
    </article>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="col-span-2 flex min-w-0 flex-col gap-[7px]">
      <span className="font-sans text-[10px] tracking-[1.5px] text-muted-2">{label}</span>
      {children}
    </div>
  );
}
