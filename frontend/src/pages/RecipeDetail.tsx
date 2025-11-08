import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getRecipeById } from '../services/api';
import { Recipe } from '../types';
import { Container, Typography, CircularProgress, Box, Paper } from '@mui/material';

const RecipeDetail = () => {
  const { recipe_id } = useParams<{ recipe_id: string }>();
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchRecipe = async () => {
      if (!recipe_id) return;
      try {
        const data = await getRecipeById(recipe_id);
        if (data) {
          setRecipe(data);
        } else {
          setError('Recipe not found.');
        }
      } catch (err) {
        setError('Failed to fetch recipe.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchRecipe();
  }, [recipe_id]);

  if (loading) {
    return <CircularProgress />;
  }

  if (error) {
    return <Typography color="error">{error}</Typography>;
  }

  if (!recipe) {
    return <Typography>Recipe not found.</Typography>;
  }

  return (
    <Container maxWidth="md">
      <Paper sx={{ p: 3, mt: 3 }}>
        <Typography variant="h4" gutterBottom>
          {recipe.name}
        </Typography>
        <Box sx={{ mt: 2 }}>
          <Typography variant="h6">Ingredients</Typography>
          <ul>
            {recipe.ingredients.map((ingredient, index) => (
              <li key={index}>
                <Typography>{ingredient}</Typography>
              </li>
            ))}
          </ul>
        </Box>
        <Box sx={{ mt: 2 }}>
          <Typography variant="h6">Instructions</Typography>
          <Typography style={{ whiteSpace: 'pre-wrap' }}>{recipe.instructions}</Typography>
        </Box>
      </Paper>
    </Container>
  );
};

export default RecipeDetail;
