import AsyncStorage from "@react-native-async-storage/async-storage";
import TcpSocket from "react-native-tcp-socket";
import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  AppState,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { PocketTcpClient } from "../services/pocket-tcp-client.cjs";

const PORT = 18080;
const ADDRESS_KEY = "yingxuPocketAddress";
const STATUS_LABELS: Record<string, string> = {
  idle: "空闲",
  scanning: "正在扫描",
  metadata: "读取素材信息",
  copying: "正在备份",
  reviewing: "正在审片",
  previewing: "正在预览",
  verifying: "正在校验",
  done: "备份完成",
  error: "任务遇到问题",
};

type Notes = { event: string; location: string; device: string; notes: string };
const EMPTY_NOTES: Notes = { event: "", location: "", device: "", notes: "" };

function isPrivateIPv4(address: string) {
  const parts = address.trim().split(".");
  if (parts.length !== 4 || parts.some((part) => !/^\d{1,3}$/.test(part))) return false;
  const octets = parts.map(Number);
  if (octets.some((part) => part < 0 || part > 255)) return false;
  const [first, second] = octets;
  return first === 10 || (first === 192 && second === 168) ||
    (first === 172 && second >= 16 && second <= 31);
}

function formatCount(value: unknown) {
  const count = Number(value || 0);
  return Number.isFinite(count) ? String(Math.max(0, count)) : "0";
}

export default function PocketHome() {
  const clientRef = useRef<PocketTcpClient | null>(null);
  const tokenRef = useRef("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [address, setAddress] = useState("");
  const [code, setCode] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState<Record<string, any> | null>(null);
  const [history, setHistory] = useState<Record<string, any>[]>([]);
  const [notes, setNotes] = useState<Notes>(EMPTY_NOTES);
  const [savingNotes, setSavingNotes] = useState(false);
  const [savedMessage, setSavedMessage] = useState("");

  useEffect(() => {
    AsyncStorage.getItem(ADDRESS_KEY).then((saved) => {
      if (saved) setAddress(saved);
    }).catch(() => {});

    const subscription = AppState.addEventListener("change", (nextState) => {
      if (nextState !== "active" && clientRef.current) {
        resetConnection("应用进入后台，已关闭本次配对连接；返回后请重新配对。");
      }
    });
    return () => {
      subscription.remove();
      resetConnection("");
    };
  }, []);

  function resetConnection(message: string) {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = null;
    const client = clientRef.current;
    clientRef.current = null;
    if (client) client.close();
    tokenRef.current = "";
    setConnected(false);
    setConnecting(false);
    setStatus(null);
    setHistory([]);
    setError(message);
  }

  async function refreshAll(client: PocketTcpClient, token: string) {
    const [statusResult, historyResult, notesResult] = await Promise.all([
      client.request("status", { token }),
      client.request("history", { token, limit: 20 }),
      client.request("notes.get", { token }),
    ]);
    setStatus(statusResult.data || {});
    setHistory(Array.isArray(historyResult.items) ? historyResult.items : []);
    setNotes({ ...EMPTY_NOTES, ...(notesResult.notes || {}) });
    setError("");
  }

  async function connect() {
    const host = address.trim();
    const pairingCode = code.trim();
    if (!isPrivateIPv4(host) || !/^\d{6}$/.test(pairingCode)) {
      setError("请输入电脑的私有局域网 IPv4 地址和 6 位配对码。");
      return;
    }

    setConnecting(true);
    setError("");
    const client = new PocketTcpClient((options) =>
      TcpSocket.createConnection(options as any, () => {}),
    );
    clientRef.current = client;
    try {
      await client.connect(host, PORT);
      const paired = await client.request("pair", { code: pairingCode });
      if (clientRef.current !== client || typeof paired.token !== "string") {
        throw new Error("配对响应无效");
      }
      tokenRef.current = paired.token;
      setCode("");
      setConnected(true);
      await AsyncStorage.setItem(ADDRESS_KEY, host).catch(() => {});
      await refreshAll(client, paired.token);
      if (clientRef.current === client && tokenRef.current) {
        pollRef.current = setInterval(() => {
          refreshAll(client, paired.token).catch((cause) => {
            resetConnection(`${cause instanceof Error ? cause.message : "读取桌面状态失败"}；请重新连接。`);
          });
        }, 15_000);
      }
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "连接失败";
      if (clientRef.current === client) resetConnection(message);
    } finally {
      setConnecting(false);
    }
  }

  async function disconnect() {
    const client = clientRef.current;
    const token = tokenRef.current;
    if (client && token) {
      await client.request("disconnect", { token }).catch(() => {});
    }
    resetConnection("");
  }

  async function saveNotes() {
    const client = clientRef.current;
    const token = tokenRef.current;
    if (!client || !token) return;
    setSavingNotes(true);
    setSavedMessage("");
    try {
      const result = await client.request("notes.save", { token, data: notes });
      setNotes({ ...EMPTY_NOTES, ...(result.notes || {}) });
      setSavedMessage("拍摄信息已保存到电脑");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "保存失败");
    } finally {
      setSavingNotes(false);
    }
  }

  const progress = status?.progress || {};
  const percent = Math.max(0, Math.min(100, Number(progress.phase_progress || 0)));

  return (
    <SafeAreaView style={styles.safeArea} edges={["top", "bottom"]}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <View style={styles.header}>
            <View>
              <Text style={styles.eyebrow}>影序 · 桌面协作</Text>
              <Text style={styles.title}>Pocket</Text>
            </View>
            <View style={[styles.connectionPill, connected && styles.connectionPillOn]}>
              <View style={[styles.connectionDot, connected && styles.connectionDotOn]} />
              <Text style={styles.connectionPillText}>{connected ? "已连接" : "未连接"}</Text>
            </View>
          </View>

          {!connected ? (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>连接影序桌面端</Text>
              <Text style={styles.bodyText}>手机和电脑需在同一局域网。Pocket 只读取备份状态、历史摘要和拍摄备注，不传输照片或视频。</Text>
              <Text style={styles.fieldLabel}>电脑局域网 IPv4 地址</Text>
              <TextInput
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="decimal-pad"
                placeholder="例如 192.168.1.20"
                placeholderTextColor="#99958E"
                value={address}
                onChangeText={setAddress}
                style={styles.input}
                accessibilityLabel="电脑局域网 IPv4 地址"
              />
              <Text style={styles.fieldLabel}>6 位配对码</Text>
              <TextInput
                keyboardType="number-pad"
                maxLength={6}
                placeholder="输入桌面端显示的配对码"
                placeholderTextColor="#99958E"
                value={code}
                onChangeText={(value) => setCode(value.replace(/\D/g, "").slice(0, 6))}
                style={styles.input}
                accessibilityLabel="6 位配对码"
                secureTextEntry
              />
              {!!error && <Text style={styles.errorText}>{error}</Text>}
              <Pressable
                accessibilityRole="button"
                disabled={connecting}
                onPress={connect}
                style={({ pressed }) => [styles.primaryButton, pressed && styles.pressed, connecting && styles.disabled]}
              >
                {connecting ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>连接桌面端</Text>}
              </Pressable>
              <Text style={styles.smallHint}>配对码和会话令牌仅保存在内存中。应用进入后台时会关闭连接并由桌面端撤销配对。</Text>
            </View>
          ) : (
            <>
              <View style={styles.statusCard}>
                <View style={styles.statusTop}>
                  <View>
                    <Text style={styles.statusLabel}>桌面工作状态</Text>
                    <Text style={styles.statusValue}>{STATUS_LABELS[status?.status] || status?.status || "连接中"}</Text>
                  </View>
                  <Pressable onPress={disconnect} accessibilityRole="button" style={styles.disconnectButton}>
                    <Text style={styles.disconnectText}>断开</Text>
                  </Pressable>
                </View>
                {!!status?.source && <Text style={styles.statusSource}>来源：{status.source}</Text>}
                <View style={styles.progressTrack}><View style={[styles.progressFill, { width: `${percent}%` }]} /></View>
                <Text style={styles.progressText}>{Math.round(percent)}% · 已处理 {formatCount(progress.processed_files)} / {formatCount(progress.total_files)} 项</Text>
                <View style={styles.statsRow}>
                  <Stat label="已完成" value={formatCount(progress.copied_files)} />
                  <Stat label="已校验" value={formatCount(progress.verified_files)} />
                  <Stat label="异常" value={formatCount(progress.failed_files)} />
                </View>
              </View>

              <View style={styles.sectionHeader}>
                <Text style={styles.sectionTitle}>最近备份</Text>
                <Text style={styles.sectionMeta}>{history.length} 条</Text>
              </View>
              <View style={styles.card}>
                {history.length === 0 ? <Text style={styles.bodyText}>还没有备份记录。</Text> : history.map((item, index) => (
                  <View key={String(item.id ?? index)} style={[styles.historyRow, index > 0 && styles.rowDivider]}>
                    <View style={styles.historyMain}>
                      <Text style={styles.historyTitle} numberOfLines={1}>{item.event_name || "未命名任务"}</Text>
                      <Text style={styles.historyMeta}>{item.target || "本机"} · {item.started_at || "时间未知"}</Text>
                    </View>
                    <Text style={styles.historyCount}>{formatCount(item.total_files)} 项</Text>
                  </View>
                ))}
              </View>

              <View style={styles.sectionHeader}>
                <Text style={styles.sectionTitle}>拍摄信息</Text>
                <Text style={styles.sectionMeta}>同步到电脑</Text>
              </View>
              <View style={styles.card}>
                <NoteField label="事件" value={notes.event} onChange={(value) => setNotes({ ...notes, event: value })} />
                <NoteField label="地点" value={notes.location} onChange={(value) => setNotes({ ...notes, location: value })} />
                <NoteField label="设备" value={notes.device} onChange={(value) => setNotes({ ...notes, device: value })} />
                <NoteField label="备注" value={notes.notes} onChange={(value) => setNotes({ ...notes, notes: value })} multiline />
                {!!savedMessage && <Text style={styles.savedText}>{savedMessage}</Text>}
                {!!error && <Text style={styles.errorText}>{error}</Text>}
                <Pressable onPress={saveNotes} disabled={savingNotes} accessibilityRole="button" style={({ pressed }) => [styles.primaryButton, pressed && styles.pressed, savingNotes && styles.disabled]}>
                  {savingNotes ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>保存拍摄信息</Text>}
                </Pressable>
              </View>
            </>
          )}

          <Text style={styles.footer}>影序 Pocket · 局域网连接 · 不上传原始素材</Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return <View style={styles.stat}><Text style={styles.statValue}>{value}</Text><Text style={styles.statLabel}>{label}</Text></View>;
}

function NoteField({ label, value, onChange, multiline = false }: { label: string; value: string; onChange: (value: string) => void; multiline?: boolean }) {
  return (
    <View style={styles.noteField}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChange}
        placeholder={`添加${label}`}
        placeholderTextColor="#99958E"
        multiline={multiline}
        style={[styles.input, multiline && styles.multilineInput]}
        textAlignVertical={multiline ? "top" : "center"}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  safeArea: { flex: 1, backgroundColor: "#F4F2ED" },
  content: { paddingHorizontal: 20, paddingBottom: 28 },
  header: { minHeight: 92, flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  eyebrow: { color: "#827D73", fontSize: 13, letterSpacing: 0.4 },
  title: { color: "#1E2420", fontSize: 34, fontWeight: "700", letterSpacing: -0.8 },
  connectionPill: { flexDirection: "row", alignItems: "center", backgroundColor: "#E8E5DF", borderRadius: 20, paddingHorizontal: 12, paddingVertical: 8 },
  connectionPillOn: { backgroundColor: "#E2EEE5" },
  connectionDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: "#99958E", marginRight: 7 },
  connectionDotOn: { backgroundColor: "#27804A" },
  connectionPillText: { color: "#41463F", fontSize: 12, fontWeight: "600" },
  card: { backgroundColor: "#FFFFFF", borderRadius: 18, padding: 18, marginBottom: 18, borderWidth: 1, borderColor: "#E9E6E0" },
  cardTitle: { color: "#232923", fontSize: 19, fontWeight: "700", marginBottom: 8 },
  bodyText: { color: "#6F706A", fontSize: 14, lineHeight: 21, marginBottom: 12 },
  fieldLabel: { color: "#4A4B45", fontSize: 12, fontWeight: "600", marginBottom: 7, marginTop: 12 },
  input: { minHeight: 48, borderColor: "#E2DFD8", borderWidth: 1, borderRadius: 11, paddingHorizontal: 13, color: "#242823", fontSize: 15, backgroundColor: "#FEFDFC" },
  multilineInput: { minHeight: 88, paddingTop: 12 },
  primaryButton: { minHeight: 50, backgroundColor: "#273D31", borderRadius: 12, alignItems: "center", justifyContent: "center", marginTop: 17 },
  primaryButtonText: { color: "#FFFFFF", fontSize: 15, fontWeight: "700" },
  pressed: { opacity: 0.82 },
  disabled: { opacity: 0.6 },
  smallHint: { color: "#86837B", fontSize: 11, lineHeight: 17, marginTop: 13 },
  errorText: { color: "#A33A32", fontSize: 13, lineHeight: 19, marginTop: 10 },
  savedText: { color: "#267444", fontSize: 13, marginTop: 10 },
  statusCard: { backgroundColor: "#253A2F", borderRadius: 20, padding: 20, marginBottom: 20 },
  statusTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" },
  statusLabel: { color: "#B9C5BA", fontSize: 12 },
  statusValue: { color: "#FFFFFF", fontSize: 24, fontWeight: "700", marginTop: 6 },
  disconnectButton: { borderWidth: 1, borderColor: "#6F8275", paddingVertical: 7, paddingHorizontal: 11, borderRadius: 10 },
  disconnectText: { color: "#E8ECE8", fontSize: 12 },
  statusSource: { color: "#CFD7D0", fontSize: 13, marginTop: 12 },
  progressTrack: { height: 7, borderRadius: 5, backgroundColor: "#516459", overflow: "hidden", marginTop: 18 },
  progressFill: { height: 7, borderRadius: 5, backgroundColor: "#DDBA76" },
  progressText: { color: "#E0E6E1", fontSize: 12, marginTop: 9 },
  statsRow: { flexDirection: "row", marginTop: 18 },
  stat: { flex: 1 },
  statValue: { color: "#FFFFFF", fontSize: 19, fontWeight: "700" },
  statLabel: { color: "#B9C5BA", fontSize: 11, marginTop: 3 },
  sectionHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "baseline", marginBottom: 10, marginTop: 2 },
  sectionTitle: { color: "#292E29", fontSize: 17, fontWeight: "700" },
  sectionMeta: { color: "#89857D", fontSize: 12 },
  historyRow: { flexDirection: "row", alignItems: "center", paddingVertical: 12 },
  rowDivider: { borderTopWidth: 1, borderTopColor: "#EFEEEA" },
  historyMain: { flex: 1, paddingRight: 10 },
  historyTitle: { color: "#343932", fontWeight: "600", fontSize: 14 },
  historyMeta: { color: "#8A877F", fontSize: 11, marginTop: 5 },
  historyCount: { color: "#77766F", fontSize: 12 },
  noteField: { marginBottom: 3 },
  footer: { color: "#9A968F", textAlign: "center", fontSize: 11, marginTop: 4 },
});
