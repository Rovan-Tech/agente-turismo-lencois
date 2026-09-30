import type { ComponentProps } from "react";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TourForm } from "../../src/components/TourForm";
import { fillTourFormRequiredFields, SAMPLE_TOUR } from "./fixtures";

type TourFormProps = ComponentProps<typeof TourForm>;

function renderCreateFormAndSubmit(
  onSubmit: TourFormProps["onSubmit"],
  onSuccess: TourFormProps["onSuccess"] = vi.fn()
) {
  render(<TourForm mode="create" onSubmit={onSubmit} onSuccess={onSuccess} onCancel={vi.fn()} />);
  fillTourFormRequiredFields("passeio-novo", "Passeio novo");
  fireEvent.click(screen.getByRole("button", { name: "Salvar" }));
}

describe("TourForm", () => {
  it("submits the create payload typed by the user", async () => {
    const onSubmit = vi.fn().mockResolvedValue({ ok: true, data: SAMPLE_TOUR });
    const onSuccess = vi.fn();

    renderCreateFormAndSubmit(onSubmit, onSuccess);

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    const [payload] = onSubmit.mock.calls[0];
    expect(payload.id).toBe("passeio-novo");
    expect(payload.nome).toBe("Passeio novo");
    expect(onSuccess).toHaveBeenCalledWith(SAMPLE_TOUR);
  });

  it("disables the id field and shows the ativo checkbox when editing", () => {
    render(
      <TourForm
        mode="edit"
        initialTour={SAMPLE_TOUR}
        onSubmit={vi.fn()}
        onSuccess={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    expect(screen.getByLabelText("Id")).toBeDisabled();
    expect(screen.getByLabelText("Ativo")).toBeChecked();
  });

  it("shows the API error message when the submission fails", async () => {
    const onSubmit = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 409, message: "já existe um passeio com esse id" });

    renderCreateFormAndSubmit(onSubmit);

    expect(await screen.findByRole("alert")).toHaveTextContent("já existe um passeio com esse id");
  });

  it("calls onCancel when the cancel button is clicked", () => {
    const onCancel = vi.fn();

    render(<TourForm mode="create" onSubmit={vi.fn()} onSuccess={vi.fn()} onCancel={onCancel} />);

    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(onCancel).toHaveBeenCalled();
  });
});
