import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import {
  loginUser,
  logoutUser,
  registerUser,
  fetchCurrentUser,
  fetchUserProfile,
  updateUserProfile,
  fetchFavorites,
  addFavorite,
  removeFavorite,
  setAccessToken,
} from '../api';

const AuthContext = createContext({});

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadAuthedData = useCallback(async () => {
    try {
      const currentUser = await fetchCurrentUser();
      setUser(currentUser);
      const [profileData, favoriteSiteIds] = await Promise.all([
        fetchUserProfile(),
        fetchFavorites(),
      ]);
      setProfile(profileData);
      setFavorites(favoriteSiteIds || []);
    } catch (err) {
      setUser(null);
      setProfile(null);
      setFavorites([]);
    }
  }, []);

  const initialize = useCallback(async () => {
    setLoading(true);
    setError(null);
    await loadAuthedData();
    setLoading(false);
  }, [loadAuthedData]);

  useEffect(() => {
    initialize();
  }, [initialize]);

  const handleLogin = useCallback(async (email, password) => {
    setError(null);
    try {
      const loginResponse = await loginUser(email, password);
      if (loginResponse?.access_token) {
        setAccessToken(loginResponse.access_token);
        await loadAuthedData();
      }
      return loginResponse;
    } catch (err) {
      setError(err);
      throw err;
    }
  }, [loadAuthedData]);

  const handleRegister = useCallback(async (email, password) => {
    setError(null);
    try {
      await registerUser(email, password);
      await handleLogin(email, password);
    } catch (err) {
      setError(err);
      throw err;
    }
  }, [handleLogin]);

  const handleLogout = useCallback(async () => {
    try {
      await logoutUser();
    } finally {
      setAccessToken(null);
      setUser(null);
      setProfile(null);
      setFavorites([]);
    }
  }, []);

  const saveProfile = useCallback(async (payload) => {
    const updated = await updateUserProfile(payload);
    setProfile(updated);
    return updated;
  }, []);

  const addFavoriteSite = useCallback(async (siteId) => {
    await addFavorite(siteId);
    setFavorites((prev) => (prev.includes(siteId) ? prev : [...prev, siteId]));
  }, []);

  const removeFavoriteSite = useCallback(async (siteId) => {
    await removeFavorite(siteId);
    setFavorites((prev) => prev.filter((id) => id !== siteId));
  }, []);

  const toggleFavoriteSite = useCallback(async (siteId) => {
    if (favorites.includes(siteId)) {
      await removeFavoriteSite(siteId);
    } else {
      await addFavoriteSite(siteId);
    }
  }, [addFavoriteSite, removeFavoriteSite, favorites]);

  const value = {
    user,
    profile,
    favorites,
    isAuthenticated: Boolean(user),
    isLoading: loading,
    error,
    login: handleLogin,
    register: handleRegister,
    logout: handleLogout,
    refresh: initialize,
    saveProfile,
    addFavoriteSite,
    removeFavoriteSite,
    toggleFavoriteSite,
    isFavorite: (siteId) => favorites.includes(siteId),
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);


