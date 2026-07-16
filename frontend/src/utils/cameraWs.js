class CameraWs {
  constructor(options) {
    this.ws = null;
    this.isConnected = false;

    this.mode = options.mode || 'cpu';
    this.conf = options.conf || 0.25;
    this.iou = options.iou || 0.45;
    this.sceneId = options.sceneId;

    this.onResult = options.onResult || (() => {});
    this.onConfigOk = options.onConfigOk || (() => {});
    this.onError = options.onError || (() => {});
    this.onClose = options.onClose || (() => {});
  }

  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.warn('[CameraWs] 已存在活跃连接');
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/detection/camera`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.isConnected = true;
      console.log('[CameraWs] 连接已建立');

      this.ws.send(
        JSON.stringify({
          type: 'config',
          mode: this.mode,
          conf: this.conf,
          iou: this.iou,
          scene_id: this.sceneId,
        }),
      );
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this._handleMessage(data);
      } catch (err) {
        console.error('[CameraWs] 消息解析失败:', err);
      }
    };

    this.ws.onclose = () => {
      this.isConnected = false;
      console.log('[CameraWs] 连接已关闭');
      this.onClose();
    };

    this.ws.onerror = (err) => {
      console.error('[CameraWs] 连接错误:', err);
      this.onError('WebSocket 连接失败，请检查后端服务');
    };
  }

  sendFrame(base64Data) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[CameraWs] 连接未建立');
      return false;
    }

    if (!base64Data) {
      return false;
    }

    this.ws.send(
      JSON.stringify({
        type: 'frame',
        data: base64Data,
      }),
    );
    return true;
  }

  close() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'close' }));
      this.ws.close();
    }
    this.ws = null;
    this.isConnected = false;
  }

  updateConfig(config) {
    this.mode = config.mode || this.mode;
    this.conf = config.conf || this.conf;
    this.iou = config.iou || this.iou;
    this.sceneId = config.sceneId;
  }

  _handleMessage(data) {
    switch (data.type) {
      case 'result':
        this.onResult({
          annotatedFrame: data.annotated_frame,
          detections: data.detections || [],
          objectCount: data.object_count || 0,
          inferenceTime: data.inference_time || 0,
          fps: data.fps || 0,
          frameCount: data.frame_count || 0,
        });
        break;

      case 'config_ok':
        console.log('[CameraWs] 配置确认:', data.message);
        this.onConfigOk(data);
        break;

      case 'error':
        console.error('[CameraWs] 服务端错误:', data.message);
        this.onError(data.message);
        break;

      default:
        console.warn('[CameraWs] 未知消息类型:', data.type);
    }
  }
}

export function createCameraWs(options) {
  return new CameraWs(options);
}