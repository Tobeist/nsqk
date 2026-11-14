"use client";
import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { animate } from "animejs";
export function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current!;
    const previous = document.activeElement;
    d.showModal();
    const anim = window.matchMedia("(prefers-reduced-motion: reduce)").matches
      ? null
      : animate(d, {
          opacity: [0, 1],
          translateY: [10, 0],
          duration: 220,
          ease: "outCubic",
        });
    return () => {
      anim?.revert();
      d.close();
      if (previous instanceof HTMLElement) previous.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className={`modal ${wide ? "wide" : ""}`}
      aria-label={title}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal-inner">
        <div className="modal-heading">
          <h2>{title}</h2>
          <button
            className="icon-button"
            aria-label="Cerrar ventana"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>
        {children}
      </div>
    </dialog>
  );
}
