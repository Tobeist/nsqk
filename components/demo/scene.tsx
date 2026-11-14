"use client";
// Adapted from Stageshow's ai-chat gold. This illustration is isolated to /demo.
import Image from "next/image";
import { FileText, ArrowRight, MapPin } from "lucide-react";
import { Stage } from "./kit/stage";
import type { Act } from "./kit/act";
import { Window, Text } from "./kit/window";
import { Collapse } from "./kit/motion/Collapse";
import { Stream } from "./kit/motion/Stream";
import { Field } from "./kit/controls/Field";
import { Button } from "./kit/controls/Button";
import { Card } from "./kit/parts/Card";
import { Chart } from "./kit/chart";
import { createDemoAnalysis, defaultSelection, signed } from "@/lib/fixtures";
import "./scene.css";
const analysis = createDemoAnalysis(defaultSelection),
  result = analysis.results[0],
  stats = result.statistics!;
const Q = "¿Qué significa esta pendiente?";
const A = `La recta cambia ${signed(stats.slopePerDecade)} °C por década en esta serie sintética. El intervalo excluye cero; esto no identifica una causa.`;
const count = A.split(" ").length;
type S = {
  analyzed: boolean;
  draft: string;
  sent: boolean;
  thinking: boolean;
  words: number;
  evidence: boolean;
};
const initial: S = {
  analyzed: false,
  draft: "",
  sent: false,
  thinking: false,
  words: 0,
  evidence: false,
};
const poster: S = {
  analyzed: true,
  draft: "",
  sent: true,
  thinking: false,
  words: count,
  evidence: true,
};
async function script(a: Act<S>) {
  await a.wait(600);
  a.mark("seleccion");
  await a.move({ at: "analyze", x: 0.8, y: 0.55 });
  await a.click();
  a.put({ analyzed: true });
  await a.wait(1400);
  a.mark("resultado");
  await a.move({ at: "composer", x: 0.3, y: 0.5 });
  await a.type("draft", Q, { interval: 35 });
  await a.wait(250);
  await a.move({ at: "send", x: 0.8, y: 0.6 });
  await a.click();
  a.put({ sent: true, draft: "", thinking: true });
  await a.wait(700);
  a.put({ thinking: false });
  a.mark("pregunta");
  for (let i = 1; i <= count; i++) {
    a.put({ words: i });
    await a.wait(62);
  }
  await a.wait(700);
  await a.move({ at: "evidence", x: 0.86, y: 0.5 });
  await a.click();
  a.put({ evidence: true });
  a.mark("evidencia");
  await a.move(
    a.layout === "compact" ? { x: 320, y: 680 } : { x: 860, y: 550 },
  );
  await a.wait(2500);
}
export default function TrendDemo() {
  return (
    <Stage
      width={940}
      height={650}
      compact={{ below: 680, width: 358, height: 700 }}
      theme="dark"
      fidelity="realistic"
      initial={initial}
      poster={poster}
      script={script}
      play="once"
      className="td-demo"
      cursor={{ at: { x: 850, y: 100 }, style: "arrow", idle: 2000 }}
    >
      {(s, _rect, layout) => (
        <DemoFrame compact={layout === "compact"}>
          <div className="td-body">
            <div className="td-context">
              <div className="td-region">
                <MapPin size={14} />
                <Text>Noreste de México</Text>
              </div>
              <div className="td-meta">
                <Text>Temperatura del aire · 1984–2024</Text>
              </div>
              {layout === "wide" && (
                <Image
                  className="td-map"
                  src="/assets/earth-fallback.svg"
                  width={230}
                  height={230}
                  alt=""
                  unoptimized
                  loading="eager"
                />
              )}
              <div className="td-analyze">
                <Button
                  variant="primary"
                  size="large"
                  data-target="analyze"
                  trailingIcon={<ArrowRight size={14} />}
                >
                  Analizar selección
                </Button>
              </div>
              <Collapse open={s.analyzed}>
                <div className="td-result">
                  <div className="td-number">
                    <Text>{signed(stats.slopePerDecade)}</Text>
                    <Text className="td-unit">°C/década</Text>
                  </div>
                  <Text className="td-data-label">Datos de demostración</Text>
                  {layout === "wide" && (
                    <Chart
                      data={result.series.map((d) => d.value!)}
                      width={230}
                      height={95}
                      show={s.analyzed}
                    />
                  )}
                </div>
              </Collapse>
            </div>
            <div className="td-conversation">
              <div className="td-chat-heading">
                <Text>Pregunta sobre este análisis</Text>
              </div>
              <div className="td-record">
                <Text className="td-record-label">CONTEXTO VERIFICABLE</Text>
                <Text wrap>
                  Una región, un periodo y una fuente para cada respuesta.
                </Text>
              </div>
              <div className="td-thread">
                <Collapse open={!s.analyzed}>
                  <div className="td-idle">
                    <Text wrap>
                      Selecciona la región y analiza la serie para comenzar.
                    </Text>
                  </div>
                </Collapse>
                <Collapse open={s.sent} reveal="drop" from="below">
                  <div className="td-question">
                    <Text wrap>{Q}</Text>
                  </div>
                </Collapse>
                <Collapse open={s.thinking}>
                  <Text className="td-thinking">
                    Preparando explicación demo…
                  </Text>
                </Collapse>
                <Collapse open={s.words > 0}>
                  <div className="td-answer">
                    <Stream text={A} count={s.words} />
                    <div className="td-evidence-action">
                      <Button
                        size="large"
                        data-target="evidence"
                        icon={<FileText size={14} />}
                      >
                        Ver evidencia
                      </Button>
                    </div>
                  </div>
                </Collapse>
                <Collapse open={s.evidence} reveal="drop">
                  <Card pad="medium" gap={10} className="td-proof">
                    <Text className="td-proof-title">
                      La cifra, con sus límites
                    </Text>
                    <Text
                      wrap
                    >{`IC 95 %: ${signed(stats.confidenceInterval[0], 3)} a ${signed(stats.confidenceInterval[1], 3)} °C/década`}</Text>
                    <Text wrap>Fuente: fixture sintética local · v1</Text>
                    <Text wrap>No permite atribuir causas ni predecir.</Text>
                  </Card>
                </Collapse>
              </div>
              <div className="td-composer-row">
                <Field
                  value={s.draft}
                  placeholder="Pregunta sobre la pendiente…"
                  className="td-composer"
                  box={{ "data-target": "composer", "data-cursor": "ibeam" }}
                />
                <Button data-target="send" size="large" variant="primary">
                  Enviar
                </Button>
              </div>
              <Text className="td-mock-label">
                Respuesta simulada · Claude no conectado
              </Text>
            </div>
          </div>
        </DemoFrame>
      )}
    </Stage>
  );
}

function DemoFrame({
  compact,
  children,
}: {
  compact: boolean;
  children: React.ReactNode;
}) {
  return compact ? (
    <Card pad="medium" className="td-compact-shell">
      {children}
    </Card>
  ) : (
    <Window
      title="Trend Detectives · demostración"
      lights="grey"
      className="td-window"
    >
      {children}
    </Window>
  );
}
