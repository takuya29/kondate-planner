import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import Recipes from './pages/Recipes';
import CreateRecipe from './pages/CreateRecipe';
import MenuPlanner from './pages/MenuPlanner';
import RecipeDetail from './pages/RecipeDetail';
import { CssBaseline } from '@mui/material';

function App() {
  return (
    <>
      <CssBaseline />
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/recipes" element={<Recipes />} />
            <Route path="/recipes/:recipe_id" element={<RecipeDetail />} />
            <Route path="/create" element={<CreateRecipe />} />
            <Route path="/planner" element={<MenuPlanner />} />
          </Routes>
        </Layout>
      </Router>
    </>
  );
}

export default App;