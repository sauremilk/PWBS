// SearchResultItem component (TASK-152)

import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import type { SearchResult } from "../types";

interface Props {
  result: SearchResult;
  onPress: () => void;
}

export function SearchResultItem({ result, onPress }: Props) {
  const score = Math.round(result.relevance_score * 100);

  return (
    <TouchableOpacity style={styles.item} onPress={onPress} activeOpacity={0.7}>
      <View style={styles.header}>
        <Text style={styles.sourceType}>{result.source_type}</Text>
        <Text style={styles.score}>{score}%</Text>
      </View>
      <Text style={styles.title} numberOfLines={1}>
        {result.title}
      </Text>
      <Text style={styles.preview} numberOfLines={2}>
        {result.content_preview}
      </Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  item: {
    backgroundColor: "#fff",
    borderRadius: 8,
    padding: 12,
    marginHorizontal: 16,
    marginVertical: 4,
    borderLeftWidth: 3,
    borderLeftColor: "#4f46e5",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 4,
  },
  sourceType: {
    fontSize: 11,
    color: "#6b7280",
    textTransform: "uppercase",
    fontWeight: "500",
  },
  score: {
    fontSize: 11,
    color: "#10b981",
    fontWeight: "600",
  },
  title: {
    fontSize: 15,
    fontWeight: "600",
    color: "#111827",
    marginBottom: 2,
  },
  preview: {
    fontSize: 13,
    color: "#6b7280",
    lineHeight: 18,
  },
});
