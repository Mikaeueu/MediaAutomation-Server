import React from "react";
import { Navigate } from "react-router-dom";
import useAuth from "../auth/useAuth";

export const ProtectedRoute: React.FC<{ children: JSX.Element }> = ({ children }) => {
  const { token } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  return children;
};
