import { genreLabel, OUTLINE_FIELD_LABEL } from "@/features/story/model/labels";
import { GENRES, type Outline, type OutlineField } from "@/features/story/model/types";
import { Chip } from "@/shared/ui/Chip";
import { FieldCard, SectionHeading } from "@/shared/ui/FieldCard";
import { SerifInput } from "@/shared/ui/fields/SerifInput";
import { TextField } from "@/shared/ui/fields/TextField";

interface OutlineEditorProps {
  outline: Outline;
  onChange(patch: Partial<Outline>): void;
  /** Fields the agent is probably rewriting right now. */
  updating: readonly OutlineField[];
  /** Fields the agent has just changed. */
  highlighted: readonly OutlineField[];
  readOnly?: boolean;
}

type TextKey = Exclude<OutlineField, "genre" | "title" | "premise">;

/** The seven always-editable outline fields in two sections. */
export function OutlineEditor({ outline: o, onChange, updating, highlighted, readOnly = false }: OutlineEditorProps) {
  const card = (key: OutlineField, num: number, span: 2 | 4, hint?: string) => ({
    num,
    label: OUTLINE_FIELD_LABEL[key],
    hint,
    updating: updating.includes(key),
    highlighted: highlighted.includes(key),
    className: span === 4 ? "col-span-4" : "col-span-2",
  });
  const text = (key: TextKey, num: number, rows: number, span: 2 | 4, hint?: string) => (
    <FieldCard {...card(key, num, span, hint)}>
      <TextField rows={rows} label={OUTLINE_FIELD_LABEL[key]} value={o[key]} readOnly={readOnly} onChange={(value) => onChange({ [key]: value })} />
    </FieldCard>
  );

  return (
    <div className="grid max-w-[1180px] min-w-[720px] grid-cols-4 gap-3">
      <SectionHeading numeral="I" title="THE PLAY" />

      <FieldCard {...card("title", 1, 2)}>
        <SerifInput
          aria-label="Title"
          placeholder="Untitled play"
          readOnly={readOnly}
          value={o.title}
          onChange={(e) => onChange({ title: e.target.value })}
          className="text-2xl"
        />
      </FieldCard>
      <FieldCard {...card("genre", 2, 2)}>
        <div className="flex flex-wrap gap-[6px]" role="group" aria-label="Genre">
          {GENRES.map((genre) => (
            <Chip key={genre} selected={o.genre === genre} disabled={readOnly} onClick={() => onChange({ genre })}>
              {genreLabel(genre).toUpperCase()}
            </Chip>
          ))}
        </div>
      </FieldCard>

      <FieldCard {...card("premise", 3, 4, "WHERE THE PLAY IS HEADED")}>
        <TextField
          rows={1}
          label="Premise"
          placeholder="Greed leads to loss"
          value={o.premise}
          readOnly={readOnly}
          onChange={(premise) => onChange({ premise })}
          className="font-serif text-2xl leading-[1.3] text-gold-light italic"
        />
      </FieldCard>

      {text("tone", 4, 2, 2)}
      {text("time_and_world", 5, 2, 2, "ERA · MILIEU")}

      <SectionHeading numeral="II" title="THE STORY" className="mt-5" />

      {text("central_conflict", 6, 2, 4, "WHO WANTS WHAT · WHAT STANDS IN THE WAY")}
      {text("synopsis", 7, 5, 4, "BEGINNING TO END")}
    </div>
  );
}
