// Search screen (TASK-152)

import React, { useState } from "react";
import {
  FlatList,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SearchResultItem } from "../components/SearchResultItem";
import { useSearch } from "../hooks/useSearch";
import type { SearchResult } from "../types";

export function SearchScreen() {
  const [query, setQuery] = useState("");
  const { data: results, isLoading } = useSearch(query);

  return (
    <View style={styles.container}>
      <View style={styles.searchBar}>
        <TextInput
          style={styles.input}
          placeholder="Wissen durchsuchen..."
          value={query}
          onChangeText={setQuery}
          autoCorrect={false}
          returnKeyType="search"
        />
      </View>

      {query.length > 0 && query.length < 2 && (
        <Text style={styles.hint}>Mindestens 2 Zeichen eingeben</Text>
      )}

      {isLoading && (
        <Text style={styles.hint}>Suche...</Text>
      )}

      {results && results.length === 0 && query.length >= 2 && !isLoading && (
        <Text style={styles.hint}>Keine Ergebnisse gefunden.</Text>
      )}

      <FlatList<SearchResult>
        data={results ?? []}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <SearchResultItem result={item} onPress={() => {}} />
        )}
        contentContainerStyle={styles.list}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f9fafb",
  },
  searchBar: {
    padding: 16,
    backgroundColor: "#fff",
    borderBottomWidth: 1,
    borderBottomColor: "#e5e7eb",
  },
  input: {
    backgroundColor: "#f3f4f6",
    borderRadius: 10,
    padding: 12,
    fontSize: 16,
  },
  hint: {
    textAlign: "center",
    color: "#9ca3af",
    fontSize: 14,
    paddingVertical: 20,
  },
  list: {
    paddingVertical: 8,
  },
});
