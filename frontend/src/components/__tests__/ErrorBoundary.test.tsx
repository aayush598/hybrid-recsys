import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import ErrorBoundary from "../../components/ErrorBoundary";

const renderWithRouter = (ui: React.ReactElement) =>
  render(<BrowserRouter>{ui}</BrowserRouter>);

describe("ErrorBoundary", () => {
  it("renders children when no error", () => {
    renderWithRouter(
      <ErrorBoundary>
        <div>Test content</div>
      </ErrorBoundary>
    );
    expect(screen.getByText("Test content")).toBeInTheDocument();
  });

  it("renders error UI when child throws", () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    const ThrowingComponent = () => {
      throw new Error("Test error");
    };

    renderWithRouter(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("Try Again")).toBeInTheDocument();
    expect(screen.getByText("Go Home")).toBeInTheDocument();

    consoleSpy.mockRestore();
  });
});
