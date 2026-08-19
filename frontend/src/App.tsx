import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import Header from "./components/layout/Header";
import HomePage from "./pages/HomePage";
import ExplorePage from "./pages/ExplorePage";
import MovieDetailPage from "./pages/MovieDetailPage";

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-surface-950">
        <Toaster
          position="bottom-right"
          toastOptions={{
            duration: 2500,
            style: {
              background: "#18181b",
              color: "#fafafa",
              border: "1px solid rgba(255,255,255,0.06)",
              borderRadius: "10px",
              fontSize: "13px",
              padding: "10px 14px",
              boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
            },
          }}
        />
        <Header />
        <main className="pt-14">
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
