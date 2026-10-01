import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { NewBookingPanel } from "../../../../../src/features/tour-booking/components/NewBookingPanel";

describe("NewBookingPanel", () => {
  it("always shows the simulation disclaimer", () => {
    render(<NewBookingPanel data="2026-09-28" onSubmit={vi.fn()} />);

    expect(screen.getByText(/Simulação — nenhum pagamento real é processado/)).toBeInTheDocument();
  });

  it("never renders a card number input, real or fake", () => {
    render(<NewBookingPanel data="2026-09-28" onSubmit={vi.fn()} />);

    fireEvent.click(screen.getByRole("radio", { name: "Cartão" }));

    expect(screen.queryByLabelText(/número do cartão/i)).toBeNull();
    expect(screen.queryByPlaceholderText(/\d{4} \d{4} \d{4} \d{4}/)).toBeNull();
    expect(screen.getAllByRole("textbox")).toHaveLength(1);
  });

  it("exposes the payment method as an accessible radio group", () => {
    render(<NewBookingPanel data="2026-09-28" onSubmit={vi.fn()} />);

    expect(screen.getByRole("group", { name: "Forma de pagamento" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Pix" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Boleto" })).not.toBeChecked();
  });

  it("switches the simulated payment preview per payment method", () => {
    render(<NewBookingPanel data="2026-09-28" onSubmit={vi.fn()} />);

    expect(screen.getByText(/QR CODE PIX SIMULADO/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("radio", { name: "Boleto" }));
    expect(screen.getByText(/BOLETO SIMULADO/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("radio", { name: "Cartão" }));
    expect(screen.getByText(/Cartão de teste/)).toBeInTheDocument();
  });

  it("submits the chosen people count, payment method and date on confirm", async () => {
    const onSubmit = vi.fn().mockResolvedValue({ ok: true });
    render(<NewBookingPanel data="2026-09-28" onSubmit={onSubmit} />);

    fireEvent.click(screen.getByRole("button", { name: "Aumentar número de pessoas" }));
    fireEvent.click(screen.getByRole("radio", { name: "Boleto" }));
    fireEvent.click(screen.getByRole("button", { name: "Simular pagamento aprovado" }));

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({
        data: "2026-09-28",
        pessoas: 2,
        forma_pagamento: "boleto",
      })
    );
  });

  it("includes the phone only when the attendant filled it in", async () => {
    const onSubmit = vi.fn().mockResolvedValue({ ok: true });
    render(<NewBookingPanel data="2026-09-28" onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Telefone (opcional)"), {
      target: { value: "5598999998888" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Simular pagamento aprovado" }));

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ telefone: "5598999998888" }))
    );
  });

  it("strips formatting from a phone typed in the common Brazilian format", async () => {
    const onSubmit = vi.fn().mockResolvedValue({ ok: true });
    render(<NewBookingPanel data="2026-09-28" onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Telefone (opcional)"), {
      target: { value: "(98) 99999-8888" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Simular pagamento aprovado" }));

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ telefone: "98999998888" }))
    );
  });

  it("shows the server error and keeps the form filled in when the booking fails", async () => {
    const onSubmit = vi.fn().mockResolvedValue({ ok: false, message: "não há vagas suficientes" });
    render(<NewBookingPanel data="2026-09-28" onSubmit={onSubmit} />);

    fireEvent.click(screen.getByRole("button", { name: "Simular pagamento aprovado" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("não há vagas suficientes");
    expect(screen.getByRole("spinbutton", { name: "Pessoas" })).toHaveValue(1);
  });

  it("resets the people count after a successful booking", async () => {
    const onSubmit = vi.fn().mockResolvedValue({ ok: true });
    render(<NewBookingPanel data="2026-09-28" onSubmit={onSubmit} />);

    fireEvent.click(screen.getByRole("button", { name: "Aumentar número de pessoas" }));
    fireEvent.click(screen.getByRole("button", { name: "Simular pagamento aprovado" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(screen.getByRole("spinbutton", { name: "Pessoas" })).toHaveValue(1);
  });

  it("never lets the people count go below one", () => {
    render(<NewBookingPanel data="2026-09-28" onSubmit={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Diminuir número de pessoas" }));

    expect(screen.getByRole("spinbutton", { name: "Pessoas" })).toHaveValue(1);
  });

  it("accepts typing the number of people directly into the field", () => {
    render(<NewBookingPanel data="2026-09-28" onSubmit={vi.fn()} />);

    fireEvent.change(screen.getByRole("spinbutton", { name: "Pessoas" }), {
      target: { value: "5" },
    });

    expect(screen.getByRole("spinbutton", { name: "Pessoas" })).toHaveValue(5);
  });
});
