import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import NotFoundPage from "../../pages/NotFoundPage";

const renderWithRouter = (ui: React.ReactElement) =>
  render(<BrowserRouter>{ui}</BrowserRouter>);

describe("NotFoundPage", () => {
  it("renders 404 text", () => {
    renderWithRouter(<NotFoundPage />);
    expect(screen.getByText("404")).toBeInTheDocument();
  });

  it("renders page not found message", () => {
    renderWithRouter(<NotFoundPage />);
    expect(screen.getByText("Page not found")).toBeInTheDocument();
  });

  it("renders home link", () => {
    renderWithRouter(<NotFoundPage />);
    expect(screen.getByText("Home")).toBeInTheDocument();
  });

  it("renders explore link", () => {
    renderWithRouter(<NotFoundPage />);
    expect(screen.getByText("Explore")).toBeInTheDocument();
  });
});
