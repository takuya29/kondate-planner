import React from 'react';
import { Dialog, DialogTitle, List, ListItem, ListItemText, ListItemButton } from '@mui/material';
import { Recipe } from '../types';

interface RecipeSelectionDialogProps {
  open: boolean;
  recipes: Recipe[];
  onClose: () => void;
  onSelect: (recipe: Recipe) => void;
}

const RecipeSelectionDialog: React.FC<RecipeSelectionDialogProps> = ({ open, recipes, onClose, onSelect }) => {
  const handleSelect = (recipe: Recipe) => {
    onSelect(recipe);
    onClose();
  };

  return (
    <Dialog onClose={onClose} open={open}>
      <DialogTitle>Select a Recipe</DialogTitle>
      <List sx={{ pt: 0 }}>
        {recipes.map((recipe) => (
          <ListItem disablePadding key={recipe.recipe_id}>
            <ListItemButton onClick={() => handleSelect(recipe)}>
              <ListItemText primary={recipe.name} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Dialog>
  );
};

export default RecipeSelectionDialog;
