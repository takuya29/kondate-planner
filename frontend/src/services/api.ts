import axios from 'axios';
import { Recipe } from '../types';

const API_URL = process.env.REACT_APP_API_URL;

const api = axios.create({
  baseURL: API_URL,
});

export const getRecipes = async (): Promise<Recipe[]> => {
  const response = await api.get('/recipes');
  return response.data.recipes;
};

export const getRecipeById = async (recipe_id: string): Promise<Recipe> => {
  const response = await api.get(`/recipes/${recipe_id}`);
  return response.data;
};

export const createRecipe = async (recipeData: Omit<Recipe, 'recipe_id'>): Promise<Recipe> => {
  const response = await api.post('/recipes', recipeData);
  return response.data;
};

