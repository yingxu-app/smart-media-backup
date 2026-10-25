import AsyncStorage from "@react-native-async-storage/async-storage";
import Constants from "expo-constants";
import TcpSocket from "react-native-tcp-socket";
import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  AppState,
  KeyboardAvoidingView,
  Linking,
  Platform,
  Pressable,
  ScrollView,
  Share,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { mediaAccess, secureStore } from "../services/media-access";
import { filterAndSortMedia, mediaTypeForName, MobileBackupEngine } from "../services/mobile-backup.cjs";
import { DesktopDownloadEngine } from "../services/desktop-download.cjs";
import { createMobileStore } from "../services/mobile-store.cjs";
import { FirebaseSyncClient } from "../services/firebase-sync.cjs";
import { PocketTcpClient } from "../services/pocket-tcp-client.cjs";

const PORT = 18080;
const ADDRESS_KEY = "yingxuPocketAddress";
const NOTES_KEY = "yingxuPocketLocalNotesV1";
const DEVICE_KEY = "yingxuFirebaseDeviceIdV1";
const FIREBASE_CONFIG = {
  apiKey: "AIzaSyA0NzN1SVbyNT2xi1HoDNn9hZQouknk-qA",
  databaseUrl: "https://yingxu-73c7b-default-rtdb.asia-southeast1.firebasedatabase.app",
};
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
  queued: "电脑离线，等待恢复连接",
  interrupted: "任务已保留，可继续",
  paused: "任务已暂停",
  cancelled: "任务已取消",
};

type Notes = { event: string; location: string; device: string; notes: string };
const EMPTY_NOTES: Notes = { event: "", location: "", device: "", notes: "" };
const mobileStore = createMobileStore(AsyncStorage);
const DEFAULT_PREFERENCES = { sortByCaptureTime: true, includeDateFolder: true, includeVideos: true, preserveSourceStructure: false };

function makeFirebaseClient(config: { apiKey: string; databaseUrl: string }, deviceId: string) {
  return new FirebaseSyncClient({ ...config, secureStore, deviceId });
}

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

function formatBytes(value: number) {
  const bytes = Math.max(0, Number(value) || 0);
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
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
  const [sourceFolder, setSourceFolder] = useState<{ uri: string; name: string } | null>(null);
  const [sourceKind, setSourceKind] = useState<"camera" | "archive">("camera");
  const [targetFolder, setTargetFolder] = useState<{ uri: string; name: string } | null>(null);
  const [extraTargetFolders, setExtraTargetFolders] = useState<{ uri: string; name: string }[]>([]);
  const [mobileFiles, setMobileFiles] = useState<any[]>([]);
  const [mobileTask, setMobileTask] = useState<Record<string, any> | null>(null);
  const [computerFiles, setComputerFiles] = useState<Record<string, any>[]>([]);
  const [selectedComputerIds, setSelectedComputerIds] = useState<string[]>([]);
  const [computerTarget, setComputerTarget] = useState<{ uri: string; name: string } | null>(null);
  const [computerImportTask, setComputerImportTask] = useState<Record<string, any> | null>(null);
  const [localHistory, setLocalHistory] = useState<Record<string, any>[]>([]);
  const [eventName, setEventName] = useState("");
  const [mobileBusy, setMobileBusy] = useState(false);
  const [firebaseEmail, setFirebaseEmail] = useState("");
  const [firebaseDisplayName, setFirebaseDisplayName] = useState("");
  const [firebasePassword, setFirebasePassword] = useState("");
  const [firebaseUser, setFirebaseUser] = useState("");
  const [cloudMessage, setCloudMessage] = useState("");
  const [cloudHistory, setCloudHistory] = useState<Record<string, any>[]>([]);
  const [expandedCloudRecordId, setExpandedCloudRecordId] = useState("");
  const [preferences, setPreferences] = useState(DEFAULT_PREFERENCES);
  const [updateMessage, setUpdateMessage] = useState("");
  const [updateUrl, setUpdateUrl] = useState("");
  const [checkingUpdate, setCheckingUpdate] = useState(false);
  const mobileEngineRef = useRef<any>(null);
  const desktopDownloadRef = useRef<any>(null);
  const computerImportTaskRef = useRef<Record<string, any> | null>(null);
  const cloudClientRef = useRef<any>(null);
  const lastCloudProgressAtRef = useRef(0);
  const cloudWatchStopsRef = useRef<(() => void)[]>([]);

  useEffect(() => {
    Promise.all([
      AsyncStorage.getItem(ADDRESS_KEY),
      AsyncStorage.getItem(NOTES_KEY),
      mobileStore.getHistory(),
      mobileStore.getActiveTask(),
      mobileStore.getFolders(),
      mobileStore.getPreferences(),
    ]).then(async ([savedAddress, savedNotes, savedHistory, savedTask, savedFolders, savedPreferences]) => {
      if (savedAddress) setAddress(savedAddress);
      if (savedNotes) setNotes({ ...EMPTY_NOTES, ...JSON.parse(savedNotes) });
      setLocalHistory(savedHistory as Record<string, any>[]);
      if (savedTask?.direction === "desktop-to-phone") {
        const restored = ["scanning", "copying", "paused"].includes(savedTask.status)
          ? { ...savedTask, status: "queued", resumeAvailable: true }
          : savedTask;
        computerImportTaskRef.current = restored as Record<string, any>;
        setComputerImportTask(restored as Record<string, any>);
      } else if (savedTask && ["scanning", "copying", "paused"].includes(savedTask.status)) {
        setMobileTask({ ...savedTask, status: "interrupted", resumeAvailable: true });
      } else if (savedTask) setMobileTask(savedTask);
      if (savedFolders.source) setSourceFolder(savedFolders.source as { uri: string; name: string });
      if (savedFolders.sourceKind === "archive") setSourceKind("archive");
      if (savedFolders.target) setTargetFolder(savedFolders.target as { uri: string; name: string });
      else mediaAccess.documentsDirectoryAsync().then(async (uri: string) => {
        const target = { uri, name: "影序手机存储" };
        setTargetFolder(target);
        await mobileStore.setFolder("target", target);
      }).catch(() => {});
      if (savedFolders.computerImportTarget) setComputerTarget(savedFolders.computerImportTarget as { uri: string; name: string });
      else mediaAccess.documentsDirectoryAsync().then(async (uri: string) => {
        const target = { uri, name: "影序手机存储" };
        setComputerTarget(target);
        await mobileStore.setFolder("computerImportTarget", target);
      }).catch(() => {});
      if (Array.isArray(savedFolders.targets)) setExtraTargetFolders(savedFolders.targets as { uri: string; name: string }[]);
      setPreferences(savedPreferences as typeof DEFAULT_PREFERENCES);
      const cloud = makeFirebaseClient(FIREBASE_CONFIG, await getDeviceId());
      cloudClientRef.current = cloud;
      cloud.restoreSession().then(async (restored: boolean) => {
        if (!restored) return;
        setFirebaseUser(cloud.session?.displayName || cloud.session?.email || "已登录");
        await refreshCloudHistory(cloud).catch(() => {});
        startCloudWatches(cloud);
        await flushCloudOutbox(cloud);
      }).catch(() => {});
    }).catch(() => {});
    mobileStore.getActiveTask().then((task) => {
      if (task?.direction !== "desktop-to-phone" && task && ["scanning", "copying", "paused"].includes(task.status)) {
        setMobileTask({ ...task, status: "interrupted", resumeAvailable: true });
      }
    }).catch(() => {});
    mobileStore.getHistory().then(setLocalHistory).catch(() => {});

    const subscription = AppState.addEventListener("change", (nextState) => {
      if (nextState !== "active") {
        const engine = mobileEngineRef.current;
        if (engine?.current?.status === "copying") engine.pause();
        if (desktopDownloadRef.current?.current?.status === "copying") desktopDownloadRef.current.queue();
        if (clientRef.current) resetConnection("应用进入后台，桌面连接已断开；本机备份任务已保留，返回后可继续。");
      } else {
        void flushCloudOutbox();
      }
    });
    return () => {
      subscription.remove();
      resetConnection("");
    };
  }, []);

  async function refreshCloudHistory(client = cloudClientRef.current) {
    if (!client?.uid) return;
    const [historyData, liveData] = await Promise.all([client.get("history"), client.get("live")]);
    const histories = (Object.values(historyData || {}) as Record<string, any>[]).sort((left, right) => String(right.startedAt || "").localeCompare(String(left.startedAt || "")));
    setCloudHistory([...(Object.values(liveData || {}) as Record<string, any>[]), ...histories].slice(0, 100));
  }

  async function getDeviceId() {
    let deviceId = await AsyncStorage.getItem(DEVICE_KEY);
    if (!deviceId) {
      deviceId = `pocket-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
      await AsyncStorage.setItem(DEVICE_KEY, deviceId);
    }
    return deviceId;
  }

  function startCloudWatches(client: any) {
    cloudWatchStopsRef.current.splice(0).forEach((stop) => stop());
    cloudWatchStopsRef.current = [
      client.watch("history", (value: any) => {
        const data = value?.data ?? value;
        setCloudHistory(Object.values(data || {}) as Record<string, any>[]);
      }, (cause: Error) => setCloudMessage(cause.message)),
      client.watch("live", (value: any) => {
        const data = value?.data ?? value;
        setCloudHistory((current) => [...Object.values(data || {}), ...current.filter((item) => item.status === "completed")].slice(0, 100) as Record<string, any>[]);
      }, (cause: Error) => setCloudMessage(cause.message)),
    ];
  }

  async function syncCloudHistory(record: Record<string, any>) {
    const client = cloudClientRef.current;
    if (!client?.uid) return;
    try {
      await client.syncHistory(record);
      await mobileStore.clearCloudHistory(record.id);
    } catch (cause) {
      await mobileStore.queueCloudHistory(record).catch(() => {});
      setCloudMessage(cause instanceof Error ? `${cause.message}；记录已保存在本机，网络恢复后会重试。` : "云端同步失败；记录已保存在本机，网络恢复后会重试。");
    }
  }

  async function publishCloudProgress(record: Record<string, any>) {
    const client = cloudClientRef.current;
    if (!client?.uid) return;
    const terminal = ["completed", "partial", "cancelled", "failed", "error"].includes(String(record.status));
    const now = Date.now();
    if (!terminal && now - lastCloudProgressAtRef.current < 2000) return;
    lastCloudProgressAtRef.current = now;
    try {
      await client.publishProgress(record);
      await mobileStore.clearCloudProgress();
      if (terminal) await mobileStore.clearCloudHistory(record.id);
    } catch (cause) {
      await mobileStore.queueCloudProgress(record).catch(() => {});
      if (terminal) await mobileStore.queueCloudHistory(record).catch(() => {});
      setCloudMessage(cause instanceof Error ? `${cause.message}；进度已保存在本机，网络恢复后会重试。` : "云端同步失败；进度已保存在本机，网络恢复后会重试。");
    }
  }

  async function flushCloudOutbox(client = cloudClientRef.current) {
    if (!client?.uid) return;
    try {
      const outbox = await mobileStore.getCloudOutbox();
      if (outbox.progress) {
        await client.publishProgress(outbox.progress);
        await mobileStore.clearCloudProgress();
      }
      for (const record of outbox.history) {
        await client.syncHistory(record);
        await mobileStore.clearCloudHistory(record.id);
      }
      const active = await mobileStore.getActiveTask();
      if (active && ["copying", "paused", "queued"].includes(String(active.status))) {
        await client.publishProgress(active);
      }
      setCloudMessage("");
    } catch (cause) {
      setCloudMessage(cause instanceof Error ? `${cause.message}；云端待同步数据仍保存在本机。` : "云端同步仍未恢复，待同步数据保存在本机。");
    }
  }

  async function pickFolder(kind: "source" | "target") {
    try {
      const picked = await mediaAccess.pickDirectoryAsync();
      if (!picked) return;
      if (kind === "source") setSourceFolder(picked);
      else setTargetFolder(picked);
      await mobileStore.setFolder(kind, picked);
      setError("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法访问所选文件夹，请重新授权。");
    }
  }

  async function setMobileSourceKind(kind: "camera" | "archive") {
    setSourceKind(kind);
    await mobileStore.setFolder("sourceKind", kind);
    setMobileFiles([]);
    setError("");
  }

  async function pickComputerTarget() {
    try {
      const picked = await mediaAccess.pickDirectoryAsync();
      if (!picked) return;
      setComputerTarget(picked);
      await mobileStore.setFolder("computerImportTarget", picked);
      setError("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法访问所选手机目标文件夹。");
    }
  }

  async function refreshComputerFiles() {
    const client = clientRef.current;
    const token = tokenRef.current;
    if (!client || !token) return setError("请先连接并配对电脑端。");
    setMobileBusy(true);
    try {
      const engine = new DesktopDownloadEngine({ client, token, mediaAccess,
        destinationRoot: computerTarget?.uri || await mediaAccess.documentsDirectoryAsync(), eventName });
      const files = await engine.listFiles();
      setComputerFiles(files);
      setSelectedComputerIds(files.map((item: any) => String(item.source_id)));
      setError(files.length ? "" : "电脑端没有可导入的素材。请先在电脑端扫描 SD 卡或素材来源。");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "读取电脑素材列表失败。");
    } finally {
      setMobileBusy(false);
    }
  }

  async function startComputerImport() {
    const client = clientRef.current;
    const token = tokenRef.current;
    const selected = computerFiles.filter((item) => selectedComputerIds.includes(String(item.source_id)));
    if (!client || !token) return setError("请先连接并配对电脑端。");
    if (!computerTarget) return setError("请先选择手机或外接存储的接收目录。");
    if (!selected.length) return setError("请先选择要导入的电脑素材。");
    await runComputerImport(selected, client, token);
  }

  async function runComputerImport(selected: Record<string, any>[], client: PocketTcpClient, token: string,
    destination: { uri: string; name: string } | null = computerTarget) {
    if (!destination) return setError("请先选择手机或外接存储的接收目录。");
    setMobileBusy(true);
    let lastBridgeStatus = "";
    let lastBridgeBytes = -8 * 1024 * 1024;
    const engine = new DesktopDownloadEngine({ client, token, mediaAccess, destinationRoot: destination.uri, eventName,
      onUpdate: (task: Record<string, any>) => {
        computerImportTaskRef.current = task;
        setComputerImportTask(task);
        mobileStore.saveActiveTask({ ...task, direction: "desktop-to-phone" }).catch(() => {});
        void publishCloudProgress(task);
        if (Platform.OS === "android") mediaAccess.startBackupForeground("影序正在接收电脑素材", `${task.processedFiles || 0} / ${task.totalFiles || 0} 项 · 已校验 ${task.verifiedFiles || 0}`).catch(() => {});
        if (task.status !== lastBridgeStatus || Number(task.bytesCopied || 0) - lastBridgeBytes >= 8 * 1024 * 1024) {
          lastBridgeStatus = task.status;
          lastBridgeBytes = Number(task.bytesCopied || 0);
          client.request("desktop.import.progress", { token, data: task }).catch(() => {});
        }
      },
    });
    desktopDownloadRef.current = engine;
    if (Platform.OS === "android") {
      const notificationsGranted = await mediaAccess.requestNotificationPermissionAsync().catch(() => false);
      if (!notificationsGranted) setError("通知权限未开启；当前前台接收可继续，切到后台后系统可能无法持续显示任务通知。");
      await mediaAccess.startBackupForeground("影序正在接收电脑素材", "准备开始传输").catch(() => {});
    }
    try {
      const record = await engine.run(selected);
      computerImportTaskRef.current = record;
      setComputerImportTask(record);
      await mobileStore.saveActiveTask({ ...record, direction: "desktop-to-phone" });
      if (record.status !== "queued") {
        const saved = await mobileStore.saveHistory({ ...record, direction: "desktop-to-phone" });
        setLocalHistory(saved as Record<string, any>[]);
        await syncCloudHistory({ ...record, direction: "desktop-to-phone" });
      }
    } finally {
      desktopDownloadRef.current = null;
      setMobileBusy(false);
      if (Platform.OS === "android") mediaAccess.stopBackupForeground().catch(() => {});
    }
  }

  async function resumeComputerImport(client: PocketTcpClient, token: string) {
    const task = computerImportTaskRef.current;
    const pending = Array.isArray(task?.pendingFiles) ? task.pendingFiles as Record<string, any>[] : [];
    if (task?.status !== "queued" || pending.length === 0) return;
    try {
      const destination = computerTarget || { uri: await mediaAccess.documentsDirectoryAsync(), name: "影序手机存储" };
      if (!computerTarget) {
        setComputerTarget(destination);
        await mobileStore.setFolder("computerImportTarget", destination);
      }
      const engine = new DesktopDownloadEngine({ client, token, mediaAccess,
        destinationRoot: destination.uri, eventName });
      const available = await engine.listFiles();
      const remaining = [...available];
      const selected: Record<string, any>[] = [];
      for (const previous of pending) {
        const index = remaining.findIndex((item) => String(item.name) === String(previous.name)
          && Number(item.size) === Number(previous.size)
          && Number(item.modified_at || 0) === Number(previous.modified_at || 0)
          && String(item.camera || "") === String(previous.camera || "")
          && String(item.captured_at || "") === String(previous.captured_at || ""));
        if (index >= 0) selected.push(remaining.splice(index, 1)[0]);
      }
      setComputerFiles(available);
      setSelectedComputerIds(selected.map((item) => String(item.source_id)));
      if (!selected.length) {
        const updated = { ...task, status: "queued", error: "电脑已连接，但扫描结果中找不到待续传素材；请检查来源盘并重新扫描。" };
        computerImportTaskRef.current = updated;
        setComputerImportTask(updated);
        await mobileStore.saveActiveTask({ ...updated, direction: "desktop-to-phone" });
        return;
      }
      await runComputerImport(selected, client, token, destination);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "电脑导入任务恢复失败。");
    }
  }

  async function addTargetFolder() {
    try {
      const picked = await mediaAccess.pickDirectoryAsync();
      if (!picked) return;
      const next = [...extraTargetFolders.filter((item) => item.uri !== picked.uri && item.uri !== targetFolder?.uri), picked];
      setExtraTargetFolders(next);
      await mobileStore.setFolder("targets", next);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法访问这个备份目标。");
    }
  }

  async function removeExtraTarget(uri: string) {
    const next = extraTargetFolders.filter((item) => item.uri !== uri);
    setExtraTargetFolders(next);
    await mobileStore.setFolder("targets", next);
  }

  async function previewMobileBackup() {
    if (!sourceFolder) return setError("请先选择 SD 卡或素材来源文件夹。");
    setMobileBusy(true);
    try {
      const files = await mediaAccess.scanMediaAsync(sourceFolder.uri);
      const supported = filterAndSortMedia(files.map((file: any) => ({ ...file, mediaType: mediaTypeForName(file.name) })), preferences);
      setMobileFiles(supported);
      setError(supported.length ? "" : "这个文件夹中没有支持的照片、RAW 或视频文件。");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "扫描文件夹失败；请检查系统文件访问授权。");
    } finally {
      setMobileBusy(false);
    }
  }

  async function startMobileBackup() {
    if (!sourceFolder) return setError("请先选择 SD 卡或素材来源文件夹。");
    if (!targetFolder) return setError("请先选择备份目标文件夹。");
    if (mobileFiles.length === 0) await previewMobileBackup();
    setMobileBusy(true);
    const transferAdapter = {
      scanMediaAsync: mediaAccess.scanMediaAsync,
      copyFileVerifiedAsync: async (sourceUri: string, destinationUri: string, relativePath: string, file: any) => {
        if (!destinationUri.startsWith("yingxu-desktop://")) {
          return mediaAccess.copyFileVerifiedAsync(sourceUri, destinationUri, relativePath);
        }
        const client = clientRef.current;
        const token = tokenRef.current;
        if (!client || !token) {
          const offline = new Error("电脑离线；任务已在手机本地排队，连接后可继续。") as Error & { code: string };
          offline.code = "DESKTOP_OFFLINE";
          throw offline;
        }
        const size = Number(file.size || 0);
        const digest = await mediaAccess.sha256Async(sourceUri);
        let offset = 0;
        try {
          await client.request("file.begin", { token, relativePath, size });
          while (offset < size) {
            const chunk = await mediaAccess.readFileChunkBase64Async(sourceUri, offset, Math.min(4096, size - offset));
            if (chunk.bytesRead <= 0) throw new Error("读取来源文件时提前结束");
            await client.request("file.chunk", { token, offset, data: chunk.data });
            offset += chunk.bytesRead;
          }
          return await client.request("file.finish", { token, sha256: digest });
        } catch (cause) {
          client.request("file.abort", { token }).catch(() => {});
          if ((client as any).isClosed?.() || /连接已断开|连接已关闭|连接超时|响应超时/.test(cause instanceof Error ? cause.message : "")) {
            const offline = new Error("电脑连接中断；任务已在手机本地排队，重连后可继续。") as Error & { code: string };
            offline.code = "DESKTOP_OFFLINE";
            throw offline;
          }
          throw cause;
        }
      },
    };
    const engine = new MobileBackupEngine({ mediaAccess: transferAdapter, onUpdate: (task: Record<string, any>) => {
      setMobileTask(task);
      mobileStore.saveActiveTask(task).catch(() => {});
      void publishCloudProgress(task);
      if (Platform.OS === "android") mediaAccess.startBackupForeground("影序正在备份素材", `${task.processedFiles || 0} / ${task.totalFiles || 0} 项 · 已校验 ${task.verifiedFiles || 0}`).catch(() => {});
    } });
    mobileEngineRef.current = engine;
    if (Platform.OS === "android") {
      const notificationsGranted = await mediaAccess.requestNotificationPermissionAsync().catch(() => false);
      if (!notificationsGranted) setError("通知权限未开启；当前前台备份可继续，但切到后台后系统可能无法持续显示任务通知。");
      await mediaAccess.startBackupForeground("影序正在扫描素材", "准备开始手机本机备份").catch(() => {});
    }
    try {
      const record = await engine.run({
        sourceUri: sourceFolder.uri,
        sourceKind,
        destinationUri: targetFolder.uri,
        eventName,
        destinationName: [targetFolder, ...extraTargetFolders].map((target) => target.name).join("、"),
        destinationTargets: [targetFolder, ...extraTargetFolders],
        taskId: ["queued", "interrupted"].includes(String(mobileTask?.status)) ? String(mobileTask?.id || "") : "",
        notes,
        preferences,
      });
      const normalized = { ...record, deviceName: "影序 Pocket", totalFiles: record.totalFiles, totalBytes: record.totalBytes };
      await mobileStore.saveActiveTask(normalized);
      if (record.status !== "queued") {
        const history = await mobileStore.saveHistory(normalized);
        setLocalHistory(history);
        await syncCloudHistory(normalized);
      }
    } finally {
      mobileEngineRef.current = null;
      setMobileBusy(false);
      if (Platform.OS === "android") mediaAccess.stopBackupForeground().catch(() => {});
    }
  }

  async function updatePreference(key: keyof typeof DEFAULT_PREFERENCES, value: boolean) {
    const next = { ...preferences, [key]: value };
    setPreferences(next);
    await mobileStore.savePreferences(next);
  }

  async function checkForUpdates() {
    setCheckingUpdate(true);
    setUpdateMessage("正在检查影序正式版本…");
    setUpdateUrl("");
    try {
      const response = await fetch("https://api.github.com/repos/yingxu-app/smart-media-backup/releases/latest", {
        headers: { Accept: "application/vnd.github+json" },
      });
      if (!response.ok) throw new Error("暂时无法连接更新服务，请检查网络后重试。");
      const release = await response.json();
      const latest = String(release.tag_name || "").replace(/^v/i, "");
      const current = String(Constants.expoConfig?.version || "未知");
      const versionKey = (version: string) => (version.match(/\d+/g) || ["0"]).slice(0, 4).map(Number);
      const latestKey = versionKey(latest);
      const currentKey = versionKey(current);
      let newer = false;
      for (let index = 0; index < Math.max(latestKey.length, currentKey.length); index += 1) {
        const latestPart = latestKey[index] || 0;
        const currentPart = currentKey[index] || 0;
        if (latestPart !== currentPart) { newer = latestPart > currentPart; break; }
      }
      const assets = Array.isArray(release.assets) ? release.assets : [];
      if (Platform.OS === "ios") {
        setUpdateMessage("iPhone 使用 Safari PWA；请刷新页面获取最新网页内容。原生 iOS App 不在当前发行范围内。");
        return;
      }
      const asset = assets.find((item: any) => String(item.name || "").toLowerCase().endsWith(".apk"));
      const releaseUrl = String(release.html_url || "https://github.com/yingxu-app/smart-media-backup/releases/latest");
      if (newer && asset?.browser_download_url) {
        setUpdateUrl(String(asset.browser_download_url));
        setUpdateMessage(`发现 v${latest} Android 更新。点击下方按钮下载；安装时请按 Android 系统提示确认。`);
      } else if (newer) {
        setUpdateUrl(releaseUrl);
        setUpdateMessage(`发现 v${latest}，但目前没有适用于此手机平台的正式安装包。`);
      } else if (latest && latest !== current) {
        setUpdateMessage(`当前 App v${current}；公开正式版为 v${latest}，暂没有较新的手机端版本。`);
      } else {
        setUpdateMessage(`当前已是最新正式版本 v${current}。`);
      }
    } catch (cause) {
      setUpdateMessage(cause instanceof Error ? cause.message : "检查更新失败，请稍后重试。");
    } finally {
      setCheckingUpdate(false);
    }
  }

  async function exportMobileReport(record: Record<string, any>) {
    const lines = [
      "影序 Pocket 备份报告",
      `记录：${record.eventName || record.sourceName || "手机备份"}`,
      `状态：${STATUS_LABELS[record.status] || record.status || "未知"}`,
      `开始：${record.startedAt || "未知"}`,
      `结束：${record.finishedAt || "未完成"}`,
      `目标：${record.destinationName || "本机"}`,
      `文件：${record.processedFiles || 0}/${record.totalFiles || 0}`,
      `已复制：${record.copiedFiles || 0}；跳过：${record.skippedFiles || 0}；已校验：${record.verifiedFiles || 0}；失败：${record.failedFiles || 0}`,
      "",
      "文件明细：",
      ...(Array.isArray(record.files) ? record.files.map((file: any) => `${file.name || "未命名"}\t${file.status || "未知"}\t${file.size || 0} bytes`) : []),
    ];
    await Share.share({ title: "影序备份报告", message: lines.join("\n") });
  }

  async function signInFirebase(createAccount = false) {
    setCloudMessage("");
    try {
      if (createAccount && !firebaseDisplayName.trim()) {
        setCloudMessage("注册时请填写用户名。");
        return;
      }
      const client = makeFirebaseClient(FIREBASE_CONFIG, await getDeviceId());
      cloudClientRef.current = client;
      const account = await client.signIn(firebaseEmail, firebasePassword, createAccount, firebaseDisplayName.trim());
      setFirebaseUser(account.displayName || account.email);
      setFirebasePassword("");
      await refreshCloudHistory(client);
      startCloudWatches(client);
      await flushCloudOutbox(client);
      setCloudMessage("已登录；同一账号的设备可同步备份进度与历史元数据。");
    } catch (cause) {
      setCloudMessage(cause instanceof Error ? cause.message : "登录失败。");
    }
  }

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
    const localNotesRaw = await AsyncStorage.getItem(NOTES_KEY).catch(() => null);
    let mergedNotes = { ...EMPTY_NOTES, ...(notesResult.notes || {}) };
    if (localNotesRaw) {
      try { mergedNotes = { ...mergedNotes, ...JSON.parse(localNotesRaw) }; } catch {}
      await client.request("notes.save", { token, data: mergedNotes }).catch(() => {});
    }
    setStatus(statusResult.data || {});
    setHistory(Array.isArray(historyResult.items) ? historyResult.items : []);
    setNotes(mergedNotes);
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
      if (computerImportTaskRef.current?.status === "queued") void resumeComputerImport(client, paired.token);
      else if (mobileTask?.status === "queued") void startMobileBackup();
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
    await AsyncStorage.setItem(NOTES_KEY, JSON.stringify(notes)).catch(() => {});
    if (!client || !token) {
      setSavedMessage("拍摄信息已保存在手机");
      return;
    }
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

  async function controlDesktopTask(command: "desktop.start" | "desktop.pause" | "desktop.cancel") {
    const client = clientRef.current;
    const token = tokenRef.current;
    if (!client || !token) return setError("请先连接桌面端。");
    try {
      await client.request(command, { token });
      await refreshAll(client, token);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "桌面任务操作失败。");
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

          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>手机本机备份</Text>
            <Text style={styles.sectionMeta}>电脑离线仍可使用</Text>
          </View>
          <View style={styles.card}>
            <Text style={styles.bodyText}>从 SD 卡、手机文件夹或旧归档中选择素材；目标可选手机存储或已授权的外接盘。所有流程只复制并校验，不会删除来源文件。</Text>
            <View style={styles.actionRow}>
              <Pressable onPress={() => setMobileSourceKind("camera")} style={sourceKind === "camera" ? styles.primaryButton : styles.secondaryButton}><Text style={sourceKind === "camera" ? styles.primaryButtonText : styles.secondaryButtonText}>备份新素材</Text></Pressable>
              <Pressable onPress={() => setMobileSourceKind("archive")} style={sourceKind === "archive" ? styles.primaryButton : styles.secondaryButton}><Text style={sourceKind === "archive" ? styles.primaryButtonText : styles.secondaryButtonText}>导入旧归档</Text></Pressable>
            </View>
            <FolderButton label={sourceKind === "archive" ? "选择旧归档来源" : "选择素材来源"} value={sourceFolder?.name || (sourceKind === "archive" ? "选择旧照片/视频归档文件夹" : "选择 SD 卡或文件夹")} onPress={() => pickFolder("source")} />
            <FolderButton label="选择备份目标" value={targetFolder?.name || "选择手机或外接盘"} onPress={() => pickFolder("target")} />
            <Pressable onPress={async () => {
              const desktop = { uri: "yingxu-desktop://paired-inbox", name: "影序电脑（局域网）" };
              setTargetFolder(desktop);
              await mobileStore.setFolder("target", desktop);
            }} style={styles.desktopTargetButton}><Text style={styles.desktopTargetText}>选择电脑为目标（未连接时会排队）</Text></Pressable>
            <Pressable onPress={addTargetFolder} style={styles.desktopTargetButton}><Text style={styles.desktopTargetText}>添加另一个手机或外接盘目标</Text></Pressable>
            {extraTargetFolders.map((target) => <Pressable key={target.uri} onLongPress={() => Alert.alert("移除此备份目标？", target.name, [{ text: "保留", style: "cancel" }, { text: "移除", style: "destructive", onPress: () => removeExtraTarget(target.uri) }])} style={styles.extraTarget}><Text style={styles.extraTargetText}>＋ {target.name}（长按移除）</Text></Pressable>)}
            <Text style={styles.fieldLabel}>分组名称（可选）</Text>
            <TextInput value={eventName} onChangeText={setEventName} placeholder="例如：冰岛自驾" placeholderTextColor="#99958E" style={styles.input} />
            <View style={styles.actionRow}>
              <Pressable onPress={previewMobileBackup} disabled={mobileBusy} style={[styles.secondaryButton, mobileBusy && styles.disabled]}>
                {mobileBusy ? <ActivityIndicator /> : <Text style={styles.secondaryButtonText}>扫描预览</Text>}
              </Pressable>
              <Pressable onPress={startMobileBackup} disabled={mobileBusy || !sourceFolder || !targetFolder} style={[styles.primaryButton, styles.rowButton, (mobileBusy || !sourceFolder || !targetFolder) && styles.disabled]}>
                {mobileBusy ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>{mobileTask?.status === "queued" || mobileTask?.status === "interrupted" ? "继续手机备份" : "开始校验备份"}</Text>}
              </Pressable>
            </View>
            {mobileFiles.length > 0 && <Text style={styles.smallHint}>扫描到 {mobileFiles.length} 个媒体文件，共 {formatBytes(mobileFiles.reduce((sum: number, file: any) => sum + Number(file.size || 0), 0))}。开始后逐个复制并做 SHA-256 校验。</Text>}
            {!!mobileTask && <View style={styles.taskPanel}>
              <Text style={styles.cardTitle}>{mobileTask.status === "completed" ? "手机备份已完成" : `手机备份：${STATUS_LABELS[mobileTask.status] || mobileTask.status}`}</Text>
              <Text style={styles.bodyText}>{formatCount(mobileTask.processedFiles)} / {formatCount(mobileTask.totalFiles)} 项 · 已校验 {formatCount(mobileTask.verifiedFiles)} · 失败 {formatCount(mobileTask.failedFiles)}</Text>
              {!!mobileTask.currentFile && <Text style={styles.smallHint} numberOfLines={1}>当前：{mobileTask.currentFile}</Text>}
              <View style={styles.actionRow}>
                <Pressable onPress={() => mobileEngineRef.current?.paused ? mobileEngineRef.current.resume() : mobileEngineRef.current?.pause()} style={styles.secondaryButton}><Text style={styles.secondaryButtonText}>{mobileEngineRef.current?.paused ? "继续" : "暂停"}</Text></Pressable>
                <Pressable onPress={() => mobileEngineRef.current?.cancel()} style={styles.cancelButton}><Text style={styles.cancelButtonText}>取消任务</Text></Pressable>
              </View>
            </View>}
            {!!error && <Text style={styles.errorText}>{error}</Text>}
            <Text style={styles.smallHint}>iOS/Android 的后台策略由系统控制；离开 App 或系统暂停后任务会保留为可恢复状态。请返回 App 后继续。外接存储授权被撤销时需重新选择。</Text>
          </View>

          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>本机历史</Text>
            <Text style={styles.sectionMeta}>{localHistory.length} 条</Text>
          </View>
          <View style={styles.card}>
            {localHistory.length === 0 ? <Text style={styles.bodyText}>完成本机备份后，记录会保存在手机上。</Text> : localHistory.slice(0, 8).map((item, index) => (
              <View key={String(item.id || index)} style={[styles.historyRow, index > 0 && styles.rowDivider]}>
                <View style={styles.historyMain}><Text style={styles.historyTitle} numberOfLines={1}>{item.eventName || item.sourceName || "手机备份"}</Text><Text style={styles.historyMeta}>{item.destinationName || "本机"} · {item.startedAt || "时间未知"}</Text></View>
                <Text style={styles.historyCount}>{formatCount(item.processedFiles)} / {formatCount(item.totalFiles)}</Text>
                <Pressable onPress={() => exportMobileReport(item)} style={styles.reportButton}><Text style={styles.reportButtonText}>导出</Text></Pressable>
              </View>
            ))}
          </View>

          <View style={styles.sectionHeader}><Text style={styles.sectionTitle}>备份偏好</Text><Text style={styles.sectionMeta}>仅保存在本机</Text></View>
          <View style={styles.card}>
            <View style={styles.preferenceRow}><Text style={styles.preferenceLabel}>优先按 EXIF 拍摄时间排序</Text><Switch value={preferences.sortByCaptureTime} onValueChange={(value) => updatePreference("sortByCaptureTime", value)} /></View>
            <View style={[styles.preferenceRow, styles.rowDivider]}><Text style={styles.preferenceLabel}>目录中包含拍摄日期</Text><Switch value={preferences.includeDateFolder} onValueChange={(value) => updatePreference("includeDateFolder", value)} /></View>
            <View style={[styles.preferenceRow, styles.rowDivider]}><Text style={styles.preferenceLabel}>备份视频</Text><Switch value={preferences.includeVideos} onValueChange={(value) => updatePreference("includeVideos", value)} /></View>
            <View style={[styles.preferenceRow, styles.rowDivider]}><Text style={styles.preferenceLabel}>导入旧归档时保留原目录结构</Text><Switch value={preferences.preserveSourceStructure} onValueChange={(value) => updatePreference("preserveSourceStructure", value)} /></View>
            <Text style={styles.smallHint}>关闭视频备份后，扫描预览和新任务都会跳过视频文件。相机 RAW 文件仍按照片处理；旧归档可选择保留原有子目录。</Text>
          </View>

          <View style={styles.sectionHeader}><Text style={styles.sectionTitle}>软件更新</Text><Text style={styles.sectionMeta}>当前 v{Constants.expoConfig?.version || "未知"}</Text></View>
          <View style={styles.card}>
            <Text style={styles.bodyText}>检查 Android 原生 App 正式发行版。iPhone 使用 Safari PWA，请刷新页面获取最新内容。</Text>
            <View style={styles.actionRow}>
              <Pressable onPress={checkForUpdates} disabled={checkingUpdate} style={[styles.primaryButton, checkingUpdate && styles.disabled]}>
                <Text style={styles.primaryButtonText}>{checkingUpdate ? "正在检查…" : "检查更新"}</Text>
              </Pressable>
              {!!updateUrl && <Pressable onPress={() => Linking.openURL(updateUrl).catch(() => setUpdateMessage("无法打开更新页面，请检查设备网络。"))} style={styles.secondaryButton}>
                <Text style={styles.secondaryButtonText}>下载更新</Text>
              </Pressable>}
            </View>
            {!!updateMessage && <Text style={styles.smallHint}>{updateMessage}</Text>}
          </View>

          <View style={styles.sectionHeader}><Text style={styles.sectionTitle}>异地进度与历史</Text><Text style={styles.sectionMeta}>{firebaseUser || "未登录"}</Text></View>
          <View style={styles.card}>
            <Text style={styles.bodyText}>Firebase 账号仅同步备份元数据；照片、视频、电脑路径和凭据不会进入云端。Firebase Spark 免费额度不是服务稳定性承诺。</Text>
            <TextInput autoCapitalize="none" keyboardType="email-address" value={firebaseEmail} onChangeText={setFirebaseEmail} placeholder="邮箱" placeholderTextColor="#99958E" style={[styles.input, styles.cloudInput]} />
            <TextInput value={firebaseDisplayName} onChangeText={setFirebaseDisplayName} maxLength={40} placeholder="用户名（注册必填；已有账号可修改）" placeholderTextColor="#99958E" style={[styles.input, styles.cloudInput]} />
            <TextInput secureTextEntry value={firebasePassword} onChangeText={setFirebasePassword} placeholder="密码（只用于登录，不保存）" placeholderTextColor="#99958E" style={[styles.input, styles.cloudInput]} />
            <View style={styles.actionRow}>
              <Pressable onPress={() => signInFirebase(false)} style={styles.secondaryButton}><Text style={styles.secondaryButtonText}>登录</Text></Pressable>
              <Pressable onPress={() => signInFirebase(true)} style={[styles.primaryButton, styles.rowButton]}><Text style={styles.primaryButtonText}>注册账号</Text></Pressable>
            </View>
            {firebaseUser ? <Pressable onPress={async () => { cloudWatchStopsRef.current.splice(0).forEach((stop) => stop()); await cloudClientRef.current?.signOut(); setFirebaseUser(""); setFirebaseDisplayName(""); setCloudHistory([]); }}><Text style={styles.smallHint}>退出账号</Text></Pressable> : null}
            {!!cloudMessage && <Text style={styles.smallHint}>{cloudMessage}</Text>}
            {cloudHistory.slice(0, 100).map((item: any, index) => {
              const recordId = String(item.id || `${item.deviceId || "cloud"}-${index}`);
              const expanded = expandedCloudRecordId === recordId;
              return <View key={recordId} style={styles.cloudHistoryEntry}>
                <Pressable onPress={() => setExpandedCloudRecordId(expanded ? "" : recordId)} style={[styles.historyRow, styles.rowDivider]} accessibilityRole="button">
                  <View style={styles.historyMain}><Text style={styles.historyTitle}>{item.eventName || item.deviceName || "同步记录"}</Text><Text style={styles.historyMeta}>{item.deviceName || "设备"} · {item.targetName || "目标未知"} · {item.status || "未知状态"}</Text></View>
                  <Text style={styles.historyCount}>{formatCount(item.processedFiles)} / {formatCount(item.totalFiles)} · {expanded ? "收起" : "详情"}</Text>
                </Pressable>
                {expanded ? <View style={styles.cloudHistoryDetail}>
                  <Text style={styles.smallHint}>开始：{item.startedAt || "未知"}　结束：{item.finishedAt || "进行中"}</Text>
                  <Text style={styles.smallHint}>大小：{formatBytes(item.totalBytes)}　已复制：{formatCount(item.copiedFiles)}　已跳过：{formatCount(item.skippedFiles)}　已校验：{formatCount(item.verifiedFiles)}　失败：{formatCount(item.failedFiles)}</Text>
                  {!!item.location && <Text style={styles.smallHint}>地点：{item.location}</Text>}
                  {!!item.cameraDevice && <Text style={styles.smallHint}>设备：{item.cameraDevice}</Text>}
                  {!!item.notes && <Text style={styles.smallHint}>备注：{item.notes}</Text>}
                  {Array.isArray(item.files) && item.files.map((file: any, fileIndex: number) => <Text key={`${file.name || "file"}-${fileIndex}`} style={styles.cloudFileDetail}>{file.name || "未命名文件"} · {file.status || "未知"} · {formatBytes(file.size)}</Text>)}
                </View> : null}
              </View>;
            })}
          </View>

          {!connected ? (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>连接影序桌面端</Text>
              <Text style={styles.bodyText}>手机和电脑需在同一局域网。配对后可查看电脑进度与历史、同步拍摄备注，并在两端之间校验传输照片和视频。</Text>
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
              <Text style={styles.smallHint}>隐私说明：电脑局域网地址保存在本机；配对后连接仅用于状态、归档摘要、拍摄信息及你明确发起的局域网文件传输。电脑来源文件只向配对手机提供最近一次扫描清单中的媒体文件，电脑绝对路径不会发送。</Text>
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
                <View style={styles.actionRow}>
                  {status?.status === "idle" || status?.status === "done" || status?.status === "error" ? <Pressable onPress={() => Alert.alert("开始电脑备份？", "将使用电脑已配置的来源和目标位置开始备份。", [{ text: "取消", style: "cancel" }, { text: "开始备份", onPress: () => controlDesktopTask("desktop.start") }])} style={styles.secondaryButton}><Text style={styles.secondaryButtonText}>开始电脑备份</Text></Pressable> : null}
                  {(["copying", "verifying", "paused"].includes(String(status?.status))) ? <Pressable onPress={() => controlDesktopTask("desktop.pause")} style={styles.secondaryButton}><Text style={styles.secondaryButtonText}>{status?.status === "paused" ? "继续电脑备份" : "暂停电脑备份"}</Text></Pressable> : null}
                  {(["copying", "verifying", "paused"].includes(String(status?.status))) ? <Pressable onPress={() => Alert.alert("取消电脑备份？", "当前文件会完成或安全中止，已复制内容会保留。", [{ text: "继续备份", style: "cancel" }, { text: "取消任务", style: "destructive", onPress: () => controlDesktopTask("desktop.cancel") }])} style={styles.cancelButton}><Text style={styles.cancelButtonText}>取消</Text></Pressable> : null}
                </View>
              </View>

              <View style={styles.sectionHeader}>
                <Text style={styles.sectionTitle}>从电脑导入到手机</Text>
                <Text style={styles.sectionMeta}>{computerFiles.length} 个电脑素材</Text>
              </View>
              <View style={styles.card}>
                <Text style={styles.bodyText}>电脑端需先扫描 SD 卡或素材来源。文件通过当前配对连接分块传输到手机授权目录；手机逐个校验 SHA-256，重复文件会跳过。</Text>
                <FolderButton label="手机接收位置" value={computerTarget?.name || "选择手机或外接盘目录"} onPress={pickComputerTarget} />
                <View style={styles.actionRow}>
                  <Pressable onPress={refreshComputerFiles} disabled={mobileBusy} style={[styles.secondaryButton, mobileBusy && styles.disabled]}>
                    {mobileBusy ? <ActivityIndicator /> : <Text style={styles.secondaryButtonText}>刷新电脑素材</Text>}
                  </Pressable>
                  <Pressable onPress={startComputerImport} disabled={mobileBusy || selectedComputerIds.length === 0} style={[styles.primaryButton, styles.rowButton, (mobileBusy || selectedComputerIds.length === 0) && styles.disabled]}>
                    {mobileBusy ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>导入所选素材</Text>}
                  </Pressable>
                </View>
                {computerFiles.length > 0 && <Text style={styles.smallHint}>已选 {selectedComputerIds.length} 项 · {formatBytes(computerFiles.filter((item) => selectedComputerIds.includes(String(item.source_id))).reduce((sum, item) => sum + Number(item.size || 0), 0))}</Text>}
                {computerFiles.slice(0, 12).map((item) => {
                  const sourceId = String(item.source_id);
                  const selected = selectedComputerIds.includes(sourceId);
                  return <Pressable key={sourceId} onPress={() => setSelectedComputerIds((current) => selected ? current.filter((id) => id !== sourceId) : [...current, sourceId])} style={[styles.historyRow, styles.rowDivider]}>
                    <Text style={styles.historyCount}>{selected ? "✓" : "○"}</Text>
                    <View style={styles.historyMain}><Text style={styles.historyTitle} numberOfLines={1}>{item.name}</Text><Text style={styles.historyMeta}>{item.camera || item.captured_at || "电脑扫描素材"} · {formatBytes(item.size)}</Text></View>
                  </Pressable>;
                })}
                {computerFiles.length > 12 && <Text style={styles.smallHint}>列表显示前 12 项，导入按钮会处理全部已选素材。</Text>}
                {!!computerImportTask && <View style={styles.taskPanel}>
                  <Text style={styles.cardTitle}>电脑导入：{STATUS_LABELS[computerImportTask.status] || computerImportTask.status}</Text>
                  <Text style={styles.bodyText}>{formatCount(computerImportTask.processedFiles)} / {formatCount(computerImportTask.totalFiles)} 项 · 已校验 {formatCount(computerImportTask.verifiedFiles)} · 失败 {formatCount(computerImportTask.failedFiles)}</Text>
                  {!!computerImportTask.currentFile && <Text style={styles.smallHint} numberOfLines={1}>当前：{computerImportTask.currentFile}</Text>}
                  {!!computerImportTask.error && <Text style={styles.errorText}>{computerImportTask.error}</Text>}
                  <View style={styles.actionRow}>
                    {(["copying", "paused"].includes(String(computerImportTask.status))) && <Pressable onPress={() => desktopDownloadRef.current?.paused ? desktopDownloadRef.current.resume() : desktopDownloadRef.current?.pause()} style={styles.secondaryButton}><Text style={styles.secondaryButtonText}>{computerImportTask.status === "paused" ? "继续" : "暂停"}</Text></Pressable>}
                    {(["copying", "paused"].includes(String(computerImportTask.status))) && <Pressable onPress={() => Alert.alert("取消电脑导入？", "已校验文件会保留，当前临时文件会清理。", [{ text: "继续", style: "cancel" }, { text: "取消任务", style: "destructive", onPress: () => desktopDownloadRef.current?.cancel() }])} style={styles.cancelButton}><Text style={styles.cancelButtonText}>取消</Text></Pressable>}
                  </View>
                </View>}
                <Text style={styles.smallHint}>电脑离线或连接中断时，未完成文件会丢弃临时数据；重新配对并刷新列表后可继续，已完成文件会校验后跳过。</Text>
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

          {!connected && <View style={styles.card}>
            <Text style={styles.cardTitle}>本机拍摄信息</Text>
            <Text style={styles.bodyText}>电脑离线时仍可填写并保存在手机；连接电脑后可再同步到桌面端。</Text>
            <NoteField label="事件" value={notes.event} onChange={(value) => setNotes({ ...notes, event: value })} />
            <NoteField label="地点" value={notes.location} onChange={(value) => setNotes({ ...notes, location: value })} />
            <NoteField label="设备" value={notes.device} onChange={(value) => setNotes({ ...notes, device: value })} />
            <NoteField label="备注" value={notes.notes} onChange={(value) => setNotes({ ...notes, notes: value })} multiline />
            {!!savedMessage && <Text style={styles.savedText}>{savedMessage}</Text>}
            <Pressable onPress={saveNotes} style={styles.primaryButton}><Text style={styles.primaryButtonText}>保存到手机</Text></Pressable>
          </View>}

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

function FolderButton({ label, value, onPress }: { label: string; value: string; onPress: () => void }) {
  return <Pressable accessibilityRole="button" onPress={onPress} style={styles.folderButton}>
    <View style={styles.historyMain}><Text style={styles.fieldLabel}>{label}</Text><Text style={styles.folderValue} numberOfLines={1}>{value}</Text></View>
    <Text style={styles.folderAction}>选择</Text>
  </Pressable>;
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
  folderButton: { minHeight: 68, flexDirection: "row", alignItems: "center", paddingHorizontal: 12, borderColor: "#E2DFD8", borderWidth: 1, borderRadius: 11, marginTop: 10, backgroundColor: "#FEFDFC" },
  folderValue: { color: "#242823", fontSize: 14, fontWeight: "600" },
  folderAction: { color: "#27804A", fontSize: 13, fontWeight: "700", marginLeft: 10 },
  desktopTargetButton: { paddingVertical: 11, alignItems: "center" },
  desktopTargetText: { color: "#27804A", fontSize: 12, fontWeight: "600" },
  extraTarget: { paddingVertical: 6 },
  extraTargetText: { color: "#5A5C55", fontSize: 12 },
  cardTitle: { color: "#232923", fontSize: 19, fontWeight: "700", marginBottom: 8 },
  bodyText: { color: "#6F706A", fontSize: 14, lineHeight: 21, marginBottom: 12 },
  fieldLabel: { color: "#4A4B45", fontSize: 12, fontWeight: "600", marginBottom: 7, marginTop: 12 },
  input: { minHeight: 48, borderColor: "#E2DFD8", borderWidth: 1, borderRadius: 11, paddingHorizontal: 13, color: "#242823", fontSize: 15, backgroundColor: "#FEFDFC" },
  multilineInput: { minHeight: 88, paddingTop: 12 },
  primaryButton: { minHeight: 50, backgroundColor: "#273D31", borderRadius: 12, alignItems: "center", justifyContent: "center", marginTop: 17 },
  primaryButtonText: { color: "#FFFFFF", fontSize: 15, fontWeight: "700" },
  secondaryButton: { minHeight: 50, flex: 1, borderColor: "#273D31", borderWidth: 1, borderRadius: 12, alignItems: "center", justifyContent: "center", marginTop: 17 },
  secondaryButtonText: { color: "#273D31", fontSize: 14, fontWeight: "700" },
  cancelButton: { minHeight: 50, flex: 1, borderColor: "#A33A32", borderWidth: 1, borderRadius: 12, alignItems: "center", justifyContent: "center", marginTop: 17 },
  cancelButtonText: { color: "#A33A32", fontSize: 14, fontWeight: "700" },
  actionRow: { flexDirection: "row", gap: 10, alignItems: "stretch" },
  rowButton: { flex: 1 },
  taskPanel: { backgroundColor: "#F4F7F3", borderRadius: 13, padding: 13, marginTop: 14 },
  cloudInput: { marginTop: 10 },
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
  reportButton: { marginLeft: 10, paddingHorizontal: 10, paddingVertical: 7, borderRadius: 9, backgroundColor: "#E8EEE9" },
  reportButtonText: { color: "#273D31", fontSize: 12, fontWeight: "700" },
  cloudHistoryEntry: { borderTopColor: "#EAE8E2", borderTopWidth: StyleSheet.hairlineWidth },
  cloudHistoryDetail: { paddingBottom: 12, gap: 4 },
  cloudFileDetail: { color: "#77766F", fontSize: 11, paddingVertical: 2 },
  preferenceRow: { minHeight: 54, flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  preferenceLabel: { color: "#343932", fontSize: 14, flex: 1, paddingRight: 12 },
  noteField: { marginBottom: 3 },
  footer: { color: "#9A968F", textAlign: "center", fontSize: 11, marginTop: 4 },
});
