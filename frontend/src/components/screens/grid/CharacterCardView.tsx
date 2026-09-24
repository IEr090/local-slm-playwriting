import { motion } from "motion/react";
import { fullName } from "@/lib/text";
import { CardUpdatingOverlay } from "./CardUpdatingOverlay";
import { roleLabel, type Character, type CharacterCard } from "@/types/character";

interface CharacterCardViewProps {
  character: Character;
  card: CharacterCard;
  number: number;
  /** The card is being regenerated after an edit. */
  updating?: boolean;
  onOpen(): void;
}

/** One card of the cast grid. The name comes live from the profile; everything else from the card. */
export function CharacterCardView({ character, card, number, updating = false, onOpen }: CharacterCardViewProps) {
  return (
    <motion.button
      type="button"
      // not clickable while the card is being updated
      disabled={updating}
      aria-busy={updating}
      onClick={onOpen}
      whileHover={updating ? undefined : { y: -2 }}
      transition={{ duration: 0.15, ease: "easeOut" }}
      className={`relative box-border flex h-[244px] flex-col rounded-[10px] border border-line bg-card px-6 py-5 text-left text-ink transition-colors duration-150 ${updating ? "cursor-default" : "hover:border-gold"}`}
    >
      <span className="flex w-full items-center justify-between">
        <span className="font-sans text-[10px] tracking-[2.5px] text-gold">{roleLabel(card.role_label).toUpperCase()}</span>
        <span className="font-sans text-[11px] tracking-[2px] text-faint">{number}</span>
      </span>

      <span className="mt-[10px] block">
        <span className="block font-serif text-[27px] leading-[1.05] font-medium text-ink">{fullName(character)}</span>
        <span className="mt-1 block font-sans text-xs text-muted">{card.tagline}</span>
      </span>

      <span className="mt-[14px] flex flex-wrap gap-[6px]">
        {card.traits.map((trait) => (
          <span
            key={trait}
            className="inline-block rounded-full border border-gold/40 bg-gold/[0.078] px-[10px] py-1 font-sans text-[11px] tracking-[0.5px] text-gold-soft"
          >
            {trait}
          </span>
        ))}
      </span>

      <span className="mt-4 flex w-full flex-col gap-[6px] border-t border-dotted border-line pt-3">
        <CardLine label="WANTS" text={card.wants} />
        <CardLine label="FEARS" text={card.fears} />
      </span>

      <CardUpdatingOverlay show={updating} />
    </motion.button>
  );
}

function CardLine({ label, text }: { label: string; text: string }) {
  return (
    <span className="flex gap-[10px] font-sans text-xs leading-[1.4]">
      <span className="w-11 shrink-0 pt-px text-[10px] tracking-[1.5px] text-muted-2">{label}</span>
      <span className="text-ink-3">{text}</span>
    </span>
  );
}
