import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/shared/ui/shadcn/dialog";
import { Pill } from "@/shared/ui/Pill";

interface LeaveDialogProps {
  open: boolean;
  /** A new character is dropped, an existing one loses its edits. */
  isNew: boolean;
  onStay(): void;
  onLeave(): void;
}

/** Asks before ALL CHARACTERS drops unsaved edits. */
export function LeaveDialog({ open, isNew, onStay, onLeave }: LeaveDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onStay()}>
      <DialogContent showCloseButton={false} className="gap-3 border border-line-strong bg-card-focus p-6 ring-0 sm:max-w-md">
        <DialogTitle className="font-serif text-2xl font-medium text-ink">Leave without saving?</DialogTitle>
        <DialogDescription className="font-sans text-[13px] leading-[1.5] text-muted">
          {isNew ? "The new character will not be created." : "Your changes to this character will not be saved."}
        </DialogDescription>
        <div className="mt-3 flex justify-end gap-[10px]">
          <Pill onClick={onStay}>Stay</Pill>
          <Pill onClick={onLeave} className="border-terracotta text-terracotta hover:border-terracotta hover:text-ink">
            Leave
          </Pill>
        </div>
      </DialogContent>
    </Dialog>
  );
}
