// PWBS Mobile App entry point (TASK-152)

import React, { useCallback, useEffect, useState } from "react";
import { NavigationContainer } from "@react-navigation/native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { isAuthenticated } from "./src/api/client";
import { AppNavigator } from "./src/navigation/AppNavigator";
import { LoginScreen } from "./src/screens/LoginScreen";
import { setupPushNotifications } from "./src/utils/notifications";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 30_000,
    },
  },
});

export default function App() {
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null);

  useEffect(() => {
    isAuthenticated().then(setLoggedIn);
  }, []);

  useEffect(() => {
    if (loggedIn) {
      setupPushNotifications().catch(console.warn);
    }
  }, [loggedIn]);

  const handleLoginSuccess = useCallback(() => {
    setLoggedIn(true);
  }, []);

  // Loading state while checking auth
  if (loggedIn === null) return null;

  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <NavigationContainer>
          <StatusBar style="light" />
          {loggedIn ? (
            <AppNavigator />
          ) : (
            <LoginScreen onLoginSuccess={handleLoginSuccess} />
          )}
        </NavigationContainer>
      </QueryClientProvider>
    </SafeAreaProvider>
  );
}
