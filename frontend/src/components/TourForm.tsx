import { useState } from "react";

import type { ApiResult } from "../lib/api";
import type { DifficultyLevel, Tour } from "../types";

const DIFFICULTY_LABELS: Record<DifficultyLevel, string> = {
  baixa: "Baixa",
  media: "Média",
  alta: "Alta",
};

type FormState = Tour;

function emptyForm(): FormState {
  return {
    id: "",
    nome: "",
    descricao: "",
    dificuldade_fisica: "media",
    caminhada_areia_minutos: 0,
    acessivel_idosos: false,
    acessivel_cadeirantes: false,
    acessivel_criancas_pequenas: false,
    duracao_horas: 1,
    faixa_etaria_recomendada: "",
    preco_reais: 0,
    ativo: true,
  };
}

const INPUT_CLASSES =
  "mt-1 w-full rounded-md border border-subtle bg-surface px-3 py-2 text-primary " +
  "disabled:bg-subtle disabled:text-muted";

type TextFieldKey = "id" | "nome" | "faixa_etaria_recomendada";
type NumberFieldKey = "caminhada_areia_minutos" | "duracao_horas" | "preco_reais";
type CheckboxFieldKey =
  "acessivel_idosos" | "acessivel_cadeirantes" | "acessivel_criancas_pequenas";

const TEXT_FIELDS: { key: TextFieldKey; label: string }[] = [
  { key: "id", label: "Id" },
  { key: "nome", label: "Nome" },
  { key: "faixa_etaria_recomendada", label: "Faixa etária recomendada" },
];

const NUMBER_FIELDS: { key: NumberFieldKey; label: string; step?: number; max: number }[] = [
  { key: "caminhada_areia_minutos", label: "Caminhada na areia (minutos)", max: 600 },
  { key: "duracao_horas", label: "Duração (horas)", step: 0.5, max: 24 },
  { key: "preco_reais", label: "Preço (R$)", step: 0.01, max: 99_999_999.99 },
];

const CHECKBOX_FIELDS: { key: CheckboxFieldKey; label: string }[] = [
  { key: "acessivel_idosos", label: "Idosos" },
  { key: "acessivel_cadeirantes", label: "Cadeirantes" },
  { key: "acessivel_criancas_pequenas", label: "Crianças pequenas" },
];

function Field({
  id,
  label,
  children,
}: Readonly<{ id: string; label: string; children: React.ReactNode }>) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-primary">
        {label}
      </label>
      {children}
    </div>
  );
}

interface TourFormProps {
  mode: "create" | "edit";
  initialTour?: Tour;
  onSubmit: (payload: FormState) => Promise<ApiResult<Tour>>;
  onSuccess: (tour: Tour) => void;
  onCancel: () => void;
}

export function TourForm({
  mode,
  initialTour,
  onSubmit,
  onSuccess,
  onCancel,
}: Readonly<TourFormProps>) {
  const [form, setForm] = useState<FormState>(initialTour ?? emptyForm());
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    const result = await onSubmit(form);

    setSubmitting(false);
    if (result.ok) {
      onSuccess(result.data);
    } else {
      setError(result.message);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      aria-label={mode === "create" ? "Novo passeio" : "Editar passeio"}
      className="mt-4 space-y-4 rounded-lg border border-subtle bg-surface p-4"
    >
      {TEXT_FIELDS.map(({ key, label }) => (
        <Field key={key} id={`tour-${key}`} label={label}>
          <input
            id={`tour-${key}`}
            value={form[key]}
            disabled={key === "id" && mode === "edit"}
            onChange={(e) => setForm({ ...form, [key]: e.target.value })}
            required
            className={INPUT_CLASSES}
          />
        </Field>
      ))}

      <Field id="tour-descricao" label="Descrição">
        <textarea
          id="tour-descricao"
          value={form.descricao}
          onChange={(e) => setForm({ ...form, descricao: e.target.value })}
          required
          rows={3}
          className={INPUT_CLASSES}
        />
      </Field>

      <Field id="tour-dificuldade" label="Dificuldade física">
        <select
          id="tour-dificuldade"
          value={form.dificuldade_fisica}
          onChange={(e) =>
            setForm({ ...form, dificuldade_fisica: e.target.value as DifficultyLevel })
          }
          className={INPUT_CLASSES}
        >
          {Object.entries(DIFFICULTY_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </Field>

      {NUMBER_FIELDS.map(({ key, label, step, max }) => (
        <Field key={key} id={`tour-${key}`} label={label}>
          <input
            id={`tour-${key}`}
            type="number"
            min={0}
            max={max}
            step={step ?? 1}
            value={form[key]}
            onChange={(e) => setForm({ ...form, [key]: Number(e.target.value) })}
            className={INPUT_CLASSES}
          />
        </Field>
      ))}

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium text-primary">Acessibilidade</legend>
        {CHECKBOX_FIELDS.map(({ key, label }) => (
          <label key={key} className="flex items-center gap-2 text-sm text-primary">
            <input
              type="checkbox"
              checked={form[key]}
              onChange={(e) => setForm({ ...form, [key]: e.target.checked })}
            />
            {label}
          </label>
        ))}
      </fieldset>

      {mode === "edit" && (
        <label className="flex items-center gap-2 text-sm text-primary">
          <input
            type="checkbox"
            checked={form.ativo ?? true}
            onChange={(e) => setForm({ ...form, ativo: e.target.checked })}
          />
          <span>Ativo</span>
        </label>
      )}

      {error && (
        <p role="alert" className="text-sm text-status-error">
          {error}
        </p>
      )}

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-action px-4 py-2 text-sm font-medium text-on-action hover:bg-action-hover active:bg-action-active disabled:bg-subtle disabled:text-muted"
        >
          {submitting ? "Salvando…" : "Salvar"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-subtle px-4 py-2 text-sm font-medium text-primary hover:bg-subtle"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
