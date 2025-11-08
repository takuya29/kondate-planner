import React, { useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { getRecipes } from '../services/api';
import { Recipe } from '../types';
import { List, ListItem, ListItemButton, ListItemText, CircularProgress, Typography } from '@mui/material';

const Recipes = () => {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchRecipes = async () => {
      try {
        const data = await getRecipes();
        setRecipes(data);
      } catch (err) {
        setError('Failed to fetch recipes.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchRecipes();
  }, []);

  if (loading) {
    return <CircularProgress />;
  }

  if (error) {
    return <Typography color="error">{error}</Typography>;
  }

  return (
    <>
      <Typography variant="h4" gutterBottom>
        Recipes
      </Typography>
      <List>
        {recipes.map((recipe) => (
          <ListItem key={recipe.recipe_id} disablePadding>
            <ListItemButton component={RouterLink} to={`/recipes/${recipe.recipe_id}`}>
              <ListItemText primary={recipe.name} secondary={`Ingredients: ${recipe.ingredients.join(', ')}`} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </>
  );
};

export default Recipes;
