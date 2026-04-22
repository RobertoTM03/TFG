import { useState } from "react";
import { createRule } from "@/entities/rule/api";
import { Button } from "@/shared/ui/Button";
import { Textarea } from "@/shared/ui/Input";

const MAX_CHARS = 500;

export function RuleForm({ owner, repo, onCreated }) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed) return;
    setLoading(true);
    setError(null);
    try {
      const rule = await createRule(owner, repo, trimmed);
      setText("");
      onCreated?.(rule);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const remaining = MAX_CHARS - text.length;

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <Textarea
        label="Nueva regla de validación"
        placeholder="Ej: Todos los métodos públicos deben tener tests unitarios."
        rows={3}
        value={text}
        onChange={(e) => setText(e.target.value)}
        maxLength={MAX_CHARS}
        error={error}
        hint={`${remaining} caracteres restantes`}
      />
      <div className="flex justify-end">
        <Button type="submit" loading={loading} disabled={!text.trim()}>
          Añadir regla
        </Button>
      </div>
    </form>
  );
}
