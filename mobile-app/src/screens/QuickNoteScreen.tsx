// Quick note screen with text + voice input (TASK-152)

import React, { useCallback, useRef, useState } from "react";
import {
  Alert,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { Audio } from "expo-av";
import { createQuickNote } from "../api/client";

export function QuickNoteScreen() {
  const [text, setText] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [sending, setSending] = useState(false);
  const recordingRef = useRef<Audio.Recording | null>(null);

  const handleSendText = async () => {
    if (!text.trim()) return;
    setSending(true);
    try {
      await createQuickNote({ content: text.trim(), source: "text" });
      setText("");
      Alert.alert("Gespeichert", "Notiz wurde erfolgreich gespeichert.");
    } catch (err) {
      Alert.alert("Fehler", (err as Error).message);
    } finally {
      setSending(false);
    }
  };

  const startRecording = useCallback(async () => {
    try {
      const permission = await Audio.requestPermissionsAsync();
      if (!permission.granted) {
        Alert.alert("Berechtigung", "Mikrofonzugriff wird benoetigt.");
        return;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY,
      );
      recordingRef.current = recording;
      setIsRecording(true);
    } catch (err) {
      Alert.alert("Fehler", "Aufnahme konnte nicht gestartet werden.");
      console.error(err);
    }
  }, []);

  const stopRecording = useCallback(async () => {
    if (!recordingRef.current) return;
    setIsRecording(false);

    try {
      await recordingRef.current.stopAndUnloadAsync();
      const uri = recordingRef.current.getURI();
      recordingRef.current = null;

      if (uri) {
        setSending(true);
        // Send the voice recording URI as content for server-side transcription
        await createQuickNote({ content: "[voice:" + uri + "]", source: "voice" });
        Alert.alert("Gespeichert", "Sprachnotiz wurde erfolgreich gespeichert.");
      }
    } catch (err) {
      Alert.alert("Fehler", (err as Error).message);
    } finally {
      setSending(false);
    }
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>Schnellnotiz</Text>

      <TextInput
        style={styles.textArea}
        placeholder="Gedanken, Ideen, Notizen..."
        value={text}
        onChangeText={setText}
        multiline
        numberOfLines={6}
        textAlignVertical="top"
      />

      <TouchableOpacity
        style={[styles.sendButton, (!text.trim() || sending) && styles.disabled]}
        onPress={handleSendText}
        disabled={!text.trim() || sending}
      >
        <Text style={styles.sendButtonText}>
          {sending ? "Wird gespeichert..." : "Textnotiz speichern"}
        </Text>
      </TouchableOpacity>

      <View style={styles.divider}>
        <View style={styles.line} />
        <Text style={styles.dividerText}>oder</Text>
        <View style={styles.line} />
      </View>

      <TouchableOpacity
        style={[styles.voiceButton, isRecording && styles.voiceButtonActive]}
        onPress={isRecording ? stopRecording : startRecording}
        disabled={sending}
      >
        <Text style={styles.voiceIcon}>{isRecording ? "\u23f9" : "\ud83c\udfa4"}</Text>
        <Text style={[styles.voiceText, isRecording && styles.voiceTextActive]}>
          {isRecording ? "Aufnahme stoppen" : "Sprachnotiz aufnehmen"}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f9fafb",
    padding: 20,
  },
  heading: {
    fontSize: 20,
    fontWeight: "700",
    color: "#111827",
    marginBottom: 16,
  },
  textArea: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    minHeight: 150,
    borderWidth: 1,
    borderColor: "#e5e7eb",
    marginBottom: 12,
  },
  sendButton: {
    backgroundColor: "#4f46e5",
    borderRadius: 10,
    padding: 14,
    alignItems: "center",
  },
  sendButtonText: {
    color: "#fff",
    fontSize: 15,
    fontWeight: "600",
  },
  disabled: {
    opacity: 0.5,
  },
  divider: {
    flexDirection: "row",
    alignItems: "center",
    marginVertical: 24,
  },
  line: {
    flex: 1,
    height: 1,
    backgroundColor: "#d1d5db",
  },
  dividerText: {
    marginHorizontal: 12,
    color: "#9ca3af",
    fontSize: 13,
  },
  voiceButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 20,
    borderWidth: 2,
    borderColor: "#e5e7eb",
  },
  voiceButtonActive: {
    borderColor: "#ef4444",
    backgroundColor: "#fef2f2",
  },
  voiceIcon: {
    fontSize: 28,
    marginRight: 12,
  },
  voiceText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#374151",
  },
  voiceTextActive: {
    color: "#ef4444",
  },
});
