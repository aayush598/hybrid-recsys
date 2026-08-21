import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import MovieCard from "../../components/recommendations/MovieCard";
import type { Movie } from "../../types";

const mockMovie: Movie = {
  id: 1,
  title: "Test Movie",
  genres: "Action|Comedy",
  year: 2024,
  overview: "A test movie",
  poster_url: null,
  vote_average: 8.5,
  vote_count: 1000,
  popularity: 50.0,
};

const renderWithRouter = (ui: React.ReactElement) =>
  render(<BrowserRouter>{ui}</BrowserRouter>);

describe("MovieCard", () => {
  it("renders movie title", () => {
    renderWithRouter(<MovieCard movie={mockMovie} />);
    const titles = screen.getAllByText("Test Movie");
    expect(titles.length).toBeGreaterThanOrEqual(1);
  });

  it("renders year badge", () => {
    renderWithRouter(<MovieCard movie={mockMovie} />);
    expect(screen.getByText("2024")).toBeInTheDocument();
  });

  it("renders rating when available", () => {
    renderWithRouter(<MovieCard movie={mockMovie} />);
    expect(screen.getByText("8.5")).toBeInTheDocument();
  });

  it("renders score when showScore is true", () => {
    renderWithRouter(<MovieCard movie={mockMovie} score={0.85} showScore />);
    expect(screen.getByText("85%")).toBeInTheDocument();
  });

  it("does not render score when showScore is false", () => {
    renderWithRouter(<MovieCard movie={mockMovie} score={0.85} />);
    expect(screen.queryByText("85%")).not.toBeInTheDocument();
  });

  it("renders genres", () => {
    renderWithRouter(<MovieCard movie={mockMovie} />);
    expect(screen.getByText("Action / Comedy")).toBeInTheDocument();
  });

  it("renders explanation on hover", () => {
    renderWithRouter(
      <MovieCard movie={mockMovie} explanation="Because you liked Action movies" showScore />
    );
    expect(screen.getByText("Because you liked Action movies")).toBeInTheDocument();
  });

  it("renders algorithm label when showScore and algorithm provided", () => {
    renderWithRouter(
      <MovieCard movie={mockMovie} algorithm="collaborative" showScore />
    );
    expect(screen.getByText("collaborative")).toBeInTheDocument();
  });

  it("links to movie detail page", () => {
    renderWithRouter(<MovieCard movie={mockMovie} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/movie/1");
  });
});
