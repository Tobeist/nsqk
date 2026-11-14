"use client";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useState } from "react";
import { ArrowLeft, RotateCcw } from "lucide-react";
import "./viewer.css";
const Scene = dynamic(() => import("./scene"), {
  ssr: false,
  loading: () => <div className="demo-loading">Preparando demostración…</div>,
});
export default function DemoViewer() {
  const [run, setRun] = useState(0);
  return (
    <main className="demo-page">
      <header>
        <Link href="/">
          <ArrowLeft size={15} />
          Volver al explorador
        </Link>
        <span>DEMOSTRACIÓN · STAGESHOW</span>
      </header>
      <div className="demo-page-intro">
        <span>DEL DATO A LA EVIDENCIA</span>
        <h1>Una pregunta que puedes verificar.</h1>
        <p>
          Secuencia ilustrada independiente de la app. Datos y respuestas de
          demostración.
        </p>
      </div>
      <figure aria-label="Demostración animada de selección, resultado, pregunta y evidencia">
        <Scene key={run} />
        <figcaption>
          <span>Selección → resultado → pregunta → evidencia</span>
          <button onClick={() => setRun((r) => r + 1)}>
            <RotateCcw size={14} />
            Reproducir de nuevo
          </button>
        </figcaption>
      </figure>
      <p className="demo-page-note">
        Para explorar con tus propias selecciones,{" "}
        <Link href="/">abre la aplicación interactiva</Link>. Claude y los datos
        científicos aún no están conectados.
      </p>
    </main>
  );
}
