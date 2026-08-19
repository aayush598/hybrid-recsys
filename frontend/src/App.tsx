import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import Header from "./components/layout/Header";
import HomePage from "./pages/HomePage";
import ExplorePage from "./pages/ExplorePage";
import MovieDetailPage from "./pages/MovieDetailPage";

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-surface-900">
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: "#1e1e1e",
              color: "#fff",
              border: "1px solid rgba(255,255,255,0.1)",
            },
          }}
        />
        <Header />
        <main className="pt-16">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/explore" element={<ExplorePage />} />
            <Route path="/movie/:id" element={<MovieDetailPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
