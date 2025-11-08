import React, { useEffect, useState } from 'react';
import { getRecipes } from '../services/api';
import { Recipe } from '../types';
import { Grid, Card, CardContent, Typography, Button, CircularProgress, Box } from '@mui/material';
import RecipeSelectionDialog from '../components/RecipeSelectionDialog';

const daysOfWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

const MenuPlanner = () => {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [menu, setMenu] = useState<Record<string, Recipe | null>>({});
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedDay, setSelectedDay] = useState<string | null>(null);

  useEffect(() => {
    const fetchRecipes = async () => {
      try {
        const data = await getRecipes();
        setRecipes(data);
      } catch (err) {
        console.error("Failed to fetch recipes for planner.", err);
      } finally {
        setLoading(false);
      }
    };
    fetchRecipes();
  }, []);

  const handleOpenDialog = (day: string) => {
    setSelectedDay(day);
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setSelectedDay(null);
  };

  const handleSelectRecipe = (recipe: Recipe) => {
    if (selectedDay) {
      setMenu((prevMenu) => ({
        ...prevMenu,
        [selectedDay]: recipe,
      }));
    }
  };

  const handleClearRecipe = (day: string) => {
    setMenu((prevMenu) => ({
      ...prevMenu,
      [day]: null,
    }));
  };

  if (loading) {
    return <CircularProgress />;
  }

  return (
    <div>
      <Typography variant="h4" gutterBottom>
        Weekly Menu Planner
      </Typography>
      <Grid container spacing={2}>
        {daysOfWeek.map((day) => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={day}>
            <Card>
              <CardContent>
                <Typography variant="h6">{day}</Typography>
                {menu[day] ? (
                  <>
                    <Typography>{menu[day]?.name}</Typography>
                    <Button size="small" onClick={() => handleClearRecipe(day)} sx={{ mt: 1 }}>
                      Clear
                    </Button>
                  </>
                ) : (
                  <Typography color="textSecondary">No recipe planned</Typography>
                )}
                <Box sx={{ mt: 2 }}>
                  <Button variant="outlined" onClick={() => handleOpenDialog(day)}>
                    Add Recipe
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
      <RecipeSelectionDialog
        open={dialogOpen}
        recipes={recipes}
        onClose={handleCloseDialog}
        onSelect={handleSelectRecipe}
      />
    </div>
  );
};

export default MenuPlanner;
