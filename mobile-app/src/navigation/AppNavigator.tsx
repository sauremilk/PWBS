// App navigation with bottom tabs (TASK-152)

import React, { useState } from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { Ionicons } from "@expo/vector-icons";
import { BriefingsScreen } from "../screens/BriefingsScreen";
import { BriefingDetailScreen } from "../screens/BriefingDetailScreen";
import { SearchScreen } from "../screens/SearchScreen";
import { QuickNoteScreen } from "../screens/QuickNoteScreen";
import type { MainTabParamList, RootStackParamList } from "../types";

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator<MainTabParamList>();

function BriefingsTab() {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  if (selectedId) {
    return (
      <BriefingDetailScreen briefingId={selectedId} />
    );
  }

  return <BriefingsScreen onSelectBriefing={setSelectedId} />;
}

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ color, size }) => {
          let iconName: keyof typeof Ionicons.glyphMap = "ellipse";
          if (route.name === "Briefings") iconName = "newspaper-outline";
          else if (route.name === "Search") iconName = "search-outline";
          else if (route.name === "QuickNote") iconName = "mic-outline";
          return <Ionicons name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: "#4f46e5",
        tabBarInactiveTintColor: "#9ca3af",
        headerStyle: { backgroundColor: "#1a1a2e" },
        headerTintColor: "#fff",
      })}
    >
      <Tab.Screen
        name="Briefings"
        component={BriefingsTab}
        options={{ title: "Briefings" }}
      />
      <Tab.Screen
        name="Search"
        component={SearchScreen}
        options={{ title: "Suche" }}
      />
      <Tab.Screen
        name="QuickNote"
        component={QuickNoteScreen}
        options={{ title: "Notiz" }}
      />
    </Tab.Navigator>
  );
}

export function AppNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Main" component={MainTabs} />
    </Stack.Navigator>
  );
}
