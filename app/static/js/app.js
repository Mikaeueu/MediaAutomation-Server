/**
 * Componente Alpine.js do painel desktop.
 *
 * Le o estado inicial de ``window.__APP_INITIAL`` (preenchido pelo
 * servidor via Jinja em desktop.html). Esse padrao e mais robusto que
 * passar JSON dentro do atributo x-data, que pode quebrar com escapes.
 *
 * @returns {object} Objeto reativo do Alpine.
 */
function dashboard() {
  const initial =
    (typeof window !== 'undefined' && window.__APP_INITIAL) || {};
  console.log('[MediaServer] dashboard() init com', initial);
  return {
    // ---------- Estado da UI ----------
    activeTab: 'live',

    // ---------- Service Types ----------
    serviceTypes: [],
    selectedId: null,
    generated: null,
    copiedField: '',

    // ---------- Network info (preenchido via SSR) ----------
    network: initial.network || { ip: '', hostname: '', port: '', desktop_url: '', mobile_url: '' },

    // ---------- Shutdown ----------
    shutdownSchedules: [],
    shutdownForm: { action: 'shutdown', dateTime: '', error: '' },

    // ---------- OBS ----------
    obs: {
      config: { host: 'localhost', port: 4455, password: '', auto_connect: true },
      showPassword: false,
      status: { connected: false, recording: { active: false, timecode: '00:00:00' } },
      scenes: [],
      collections: [],
      currentCollection: null,
      modes: { studio: false, virtualCam: false, replayBuffer: false },
      testMessage: '',
      testOk: false,
      lastRecordingPath: '',
    },
    _obsPollId: null,

    // ---------- Holyrics ----------
    holy: {
      config: { host: 'localhost', port: 8091, token: '', is_configured: false },
      showToken: false,
      status: { connected: false, configured: false, current: null },
      recent: [],
      testMessage: '',
      testOk: false,
    },

    // ---------- Modal de aviso pre-shutdown ----------
    // Limiar (em minutos) para mostrar o aviso antes do disparo.
    WARNING_THRESHOLD_MIN: 5,
    warning: {
      visible: false,
      scheduleId: null,
      action: 'shutdown',
      scheduledFor: null,  // ISO string
      countdown: '',        // texto formatado HH:MM:SS
      dismissedIds: [],     // ids ja dispensados (nao mostrar de novo)
    },
    _warningTickId: null,
    _shutdownPollId: null,

    // ---------- Form de tipos de culto ----------
    showForm: false,
    form: {
      id: null,
      name: '',
      title_template: '',
      description_template: '',
      suggested_weekday: null,
    },

    // ============================================================
    //  Bootstrap
    // ============================================================

    /**
     * Bootstrap do componente.
     */
    async init() {
      await Promise.all([
        this.loadTypes(),
        this.loadShutdowns(),
      ]);

      try {
        const res = await fetch('/api/live/suggestion');
        if (res.ok) {
          const data = await res.json();
          if (data.suggestion) await this.generate(data.suggestion.id);
        }
      } catch (e) { /* sugestao indisponivel */ }

      // Polling em background para detectar shutdown proximo e disparar
      // o modal de aviso. 30s de intervalo e folgado pra janela de 5 min.
      this._shutdownPollId = setInterval(() => this._checkUpcomingShutdown(), 30 * 1000);
      this._checkUpcomingShutdown();
    },

    // ============================================================
    //  Service Types
    // ============================================================

    async loadTypes() {
      const res = await fetch('/api/service-types');
      if (res.ok) this.serviceTypes = await res.json();
    },

    async generate(id) {
      this.selectedId = id;
      const res = await fetch(`/api/live/generate/${id}`, { method: 'POST' });
      if (res.ok) this.generated = await res.json();
    },

    openForm(item = null) {
      this.form = item
        ? { ...item }
        : { id: null, name: '', title_template: '', description_template: '', suggested_weekday: null };
      this.showForm = true;
    },

    async save() {
      const isEdit = !!this.form.id;
      const url = isEdit ? `/api/service-types/${this.form.id}` : '/api/service-types';
      const method = isEdit ? 'PUT' : 'POST';

      const payload = { ...this.form };
      delete payload.id;

      if (payload.suggested_weekday === '' || payload.suggested_weekday === 'null' || payload.suggested_weekday === null) {
        payload.suggested_weekday = null;
      } else {
        payload.suggested_weekday = parseInt(payload.suggested_weekday, 10);
      }

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        this.showForm = false;
        await this.loadTypes();
      } else {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || 'Erro ao salvar.');
      }
    },

    async remove(id) {
      if (!confirm('Excluir este tipo de culto?')) return;
      const res = await fetch(`/api/service-types/${id}`, { method: 'DELETE' });
      if (res.ok) {
        if (this.selectedId === id) {
          this.generated = null;
          this.selectedId = null;
        }
        await this.loadTypes();
      }
    },

    // ============================================================
    //  Shutdown / Suspend
    // ============================================================

    /**
     * Carrega agendamentos de shutdown/suspend.
     */
    async loadShutdowns() {
      const res = await fetch('/api/shutdown');
      if (res.ok) this.shutdownSchedules = await res.json();
    },

    /**
     * Atalho: agenda para "agora + N minutos".
     *
     * @param {number} minutes Minutos a partir de agora.
     */
    quickSchedule(minutes) {
      const future = new Date(Date.now() + minutes * 60 * 1000);
      this.shutdownForm.dateTime = this._toDatetimeLocal(future);
      this.shutdownForm.error = '';
    },

    /**
     * Valor minimo (agora) para o input datetime-local.
     *
     * @returns {string} Datetime no formato YYYY-MM-DDTHH:MM.
     */
    minDateTime() {
      return this._toDatetimeLocal(new Date());
    },

    /**
     * Verifica se o horario escolhido e valido (no futuro).
     *
     * @returns {boolean}
     */
    schedulePreviewValid() {
      if (!this.shutdownForm.dateTime) return false;
      const target = new Date(this.shutdownForm.dateTime);
      return !isNaN(target.getTime()) && target.getTime() > Date.now();
    },

    /**
     * Texto absoluto formatado do agendamento ("DD/MM/YYYY as HH:MM").
     *
     * @returns {string}
     */
    schedulePreviewAbsolute() {
      if (!this.shutdownForm.dateTime) return '';
      const target = new Date(this.shutdownForm.dateTime);
      if (isNaN(target.getTime())) return '';
      const pad = (n) => String(n).padStart(2, '0');
      return `${pad(target.getDate())}/${pad(target.getMonth() + 1)}/${target.getFullYear()} ` +
             `as ${pad(target.getHours())}:${pad(target.getMinutes())}`;
    },

    /**
     * Texto relativo do agendamento ("2 horas e 15 minutos", "45 minutos", etc.).
     *
     * @returns {string}
     */
    schedulePreviewRelative() {
      if (!this.shutdownForm.dateTime) return '';
      const target = new Date(this.shutdownForm.dateTime);
      if (isNaN(target.getTime())) return '';
      let diffSec = Math.floor((target.getTime() - Date.now()) / 1000);
      if (diffSec <= 0) return '';

      const days = Math.floor(diffSec / 86400);  diffSec %= 86400;
      const hours = Math.floor(diffSec / 3600);  diffSec %= 3600;
      const minutes = Math.floor(diffSec / 60);

      const parts = [];
      if (days > 0) parts.push(`${days} dia${days > 1 ? 's' : ''}`);
      if (hours > 0) parts.push(`${hours} hora${hours > 1 ? 's' : ''}`);
      if (minutes > 0 || parts.length === 0) parts.push(`${minutes} minuto${minutes !== 1 ? 's' : ''}`);

      // junta com vírgulas e "e" antes do último
      if (parts.length === 1) return parts[0];
      const last = parts.pop();
      return parts.join(', ') + ' e ' + last;
    },

    /**
     * Envia o agendamento ao backend.
     */
    async scheduleShutdown() {
      this.shutdownForm.error = '';
      if (!this.schedulePreviewValid()) {
        this.shutdownForm.error = 'Selecione uma data e hora futura antes de agendar.';
        return;
      }

      const target = new Date(this.shutdownForm.dateTime);
      const payload = {
        scheduled_for: this._toLocalIso(target),
        action: this.shutdownForm.action,
      };

      const res = await fetch('/api/shutdown', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        this.shutdownForm.dateTime = '';
        await this.loadShutdowns();
      } else {
        const err = await res.json().catch(() => ({}));
        this.shutdownForm.error = err.detail || 'Erro ao agendar.';
      }
    },

    /**
     * Cancela um agendamento ativo (mantem o registro com status 'cancelled').
     */
    async cancelShutdown(id) {
      if (!confirm('Cancelar este agendamento?')) return;
      const res = await fetch(`/api/shutdown/${id}/cancel`, { method: 'POST' });
      if (res.ok) await this.loadShutdowns();
    },

    /**
     * Remove definitivamente um agendamento.
     */
    async deleteShutdown(id) {
      if (!confirm('Excluir definitivamente este agendamento?')) return;
      const res = await fetch(`/api/shutdown/${id}`, { method: 'DELETE' });
      if (res.ok) await this.loadShutdowns();
    },

    /**
     * Rotulo localizado para o status do agendamento.
     */
    statusLabel(status) {
      return {
        scheduled: 'Agendado',
        cancelled: 'Cancelado',
        executed:  'Executado',
      }[status] || status;
    },

    /**
     * Formata um ISO de datetime para "DD/MM/YYYY HH:MM".
     */
    formatDateTime(iso) {
      if (!iso) return '';
      const d = new Date(iso);
      if (isNaN(d.getTime())) return iso;
      const pad = (n) => String(n).padStart(2, '0');
      return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    },

    // ============================================================
    //  OBS
    // ============================================================

    /**
     * Carrega config + status quando entra na aba OBS pela primeira vez,
     * e inicia polling de status.
     */
    async obsActivate() {
      await this.obsLoadConfig();
      await this.obsRefreshAll();
      if (!this._obsPollId) {
        this._obsPollId = setInterval(() => this.obsRefreshStatus(), 5000);
      }
    },

    async obsLoadConfig() {
      const res = await fetch('/api/obs/config');
      if (res.ok) this.obs.config = await res.json();
    },

    async obsSaveConfig() {
      this.obs.testMessage = '';
      const res = await fetch('/api/obs/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host: this.obs.config.host,
          port: parseInt(this.obs.config.port, 10),
          password: this.obs.config.password || '',
          auto_connect: !!this.obs.config.auto_connect,
        }),
      });
      if (res.ok) {
        this.obs.testOk = true;
        this.obs.testMessage = 'Configuracao salva. Reconectando...';
        setTimeout(() => { this.obs.testMessage = ''; }, 3000);
        await this.obsRefreshAll();
      } else {
        const err = await res.json().catch(() => ({}));
        this.obs.testOk = false;
        this.obs.testMessage = err.detail || 'Erro ao salvar.';
      }
    },

    async obsTestConfig() {
      this.obs.testMessage = 'Testando...';
      this.obs.testOk = false;
      const res = await fetch('/api/obs/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host: this.obs.config.host,
          port: parseInt(this.obs.config.port, 10),
          password: this.obs.config.password || '',
        }),
      });
      const data = await res.json().catch(() => ({}));
      this.obs.testOk = !!data.ok;
      this.obs.testMessage = data.ok
        ? `${data.message} (OBS ${data.obs_version || ''})`
        : (data.message || 'Falha no teste');
    },

    async obsRefreshStatus() {
      try {
        const res = await fetch('/api/obs/status');
        if (res.ok) this.obs.status = await res.json();
      } catch (e) { /* offline */ }
    },

    async obsRefreshAll() {
      await this.obsRefreshStatus();
      if (this.obs.status.connected) {
        await Promise.all([
          this.obsLoadScenes(),
          this.obsLoadCollections(),
        ]);
      }
    },

    async obsReconnect() {
      this.obs.testMessage = 'Reconectando...';
      const res = await fetch('/api/obs/reconnect', { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      this.obs.testOk = !!data.connected;
      this.obs.testMessage = data.connected ? 'Conectado.' : (data.detail || 'Falha ao reconectar.');
      setTimeout(() => { this.obs.testMessage = ''; }, 3000);
      await this.obsRefreshAll();
    },

    async obsLoadScenes() {
      try {
        const res = await fetch('/api/obs/scenes');
        if (res.ok) {
          const data = await res.json();
          this.obs.scenes = data.scenes || [];
        }
      } catch (e) { /* sem conexao */ }
    },

    async obsSwitchScene(name) {
      const res = await fetch('/api/obs/scenes/activate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      if (res.ok) await this.obsRefreshStatus();
    },

    async obsOpenProjector(name) {
      await fetch('/api/obs/scenes/projector', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, monitor: -1 }),
      });
    },

    async obsHideScene(name) {
      const res = await fetch('/api/obs/scenes/hide', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      if (res.ok) await this.obsLoadScenes();
    },

    async obsUnhideScene(name) {
      const res = await fetch('/api/obs/scenes/unhide', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      if (res.ok) await this.obsLoadScenes();
    },

    async obsLoadCollections() {
      try {
        const res = await fetch('/api/obs/scene-collections');
        if (res.ok) {
          const data = await res.json();
          this.obs.collections = data.collections || [];
          this.obs.currentCollection = data.current;
        }
      } catch (e) { /* sem conexao */ }
    },

    async obsSwitchCollection(name) {
      if (!confirm(`Trocar para a coleção "${name}"? O OBS vai recarregar as cenas.`)) return;
      await fetch('/api/obs/scene-collections/activate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      // Aguarda OBS estabilizar e recarrega tudo.
      setTimeout(() => this.obsRefreshAll(), 1500);
    },

    async obsToggleRecording() {
      const res = await fetch('/api/obs/recording/toggle', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.outputPath) this.obs.lastRecordingPath = data.outputPath;
        await this.obsRefreshStatus();
      }
    },

    async obsToggleStudioMode() {
      const res = await fetch('/api/obs/studio-mode/toggle', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        this.obs.modes.studio = !!data.studio_mode;
      }
    },

    async obsToggleVirtualCam() {
      const res = await fetch('/api/obs/virtual-cam/toggle', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        this.obs.modes.virtualCam = !!data.virtual_cam;
      }
    },

    async obsToggleReplayBuffer() {
      const res = await fetch('/api/obs/replay-buffer/toggle', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        this.obs.modes.replayBuffer = !!data.replay_buffer;
      }
    },

// ============================================================
//  Holyrics (config no desktop, controle no mobile)
// ============================================================

async holyActivate() {
  // só carrega se ainda não tiver carregado
  if (!this.holy._loaded) {
    await this.holyLoadConfig();
    await this.holyLoadRecent();
    this.holy._loaded = true;
  }

  if (this.holy.config.is_configured) {
    await this.holyRefreshStatus();
  }
},

async holyLoadConfig() {
  this._log('HOLY LOAD CONFIG START');

  const { res, data } = await this._fetch('/api/holyrics/config');

  this._log('HOLY RAW RESPONSE', data);

  if (!res.ok) {
    this._log('HOLY CONFIG ERRO HTTP');
    return;
  }

  if (!data || !data.data) {
    this._log('HOLY CONFIG VAZIO → NÃO VOU SOBRESCREVER');
    return;
  }

  const cfg = data.data;

  this._log('ANTES DE ATUALIZAR', this.holy.config);

  this.holy.config = {
    host: cfg.host ?? this.holy.config.host,
    port: cfg.port ?? this.holy.config.port,
    token: cfg.token ?? this.holy.config.token,
    is_configured: !!cfg.is_configured,
  };

  this._log('DEPOIS DE ATUALIZAR', this.holy.config);
},

async holyRefreshStatus() {
  try {
    const res = await fetch('/api/holyrics/status');

    if (!res.ok) return;

    const data = await res.json();

    if (!data.ok) {
      this.holy.status.connected = false;
      this.holy.status.error = 'Sem resposta da API';
      return;
    }

    const d = data.data || {};

    // 🔥 ATUALIZA SEM DESTRUIR O OBJETO
    this.holy.status = {
      ...this.holy.status,
      connected: true,
      error: null,
      current: d.current ?? null,
      raw: d,
    };

  } catch (e) {
    this.holy.status = {
      ...this.holy.status,
      connected: false,
      error: 'Erro de conexão',
    };
  }
},

async holyLoadRecent() {
  try {
    const res = await fetch('/api/holyrics/recent');

    if (!res.ok) return;

    const data = await res.json();

    // ✅ correto
    this.holy.recent = data.data || [];

  } catch (e) {
    this.holy.recent = [];
  }
},

async holyTestConfig() {
  this.holy.testMessage = 'Testando...';
  this.holy.testOk = false;

  const res = await fetch('/api/holyrics/test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      host: this.holy.config.host,
      port: parseInt(this.holy.config.port, 10),
      token: this.holy.config.token || '',
    }),
  });

  const data = await res.json().catch(() => ({}));

  this.holy.testOk = !!data.ok;
  this.holy.testMessage = data.message || (data.ok ? 'Conectado com sucesso' : 'Falha na conexão');
},

async holySaveConfig() {
  this.holy.testMessage = 'Salvando...';
  this.holy.testOk = false;

  const payload = {
    host: this.holy.config.host,
    port: parseInt(this.holy.config.port, 10),
    token: this.holy.config.token || '',
  };

  const res = await fetch('/api/holyrics/config', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = await res.json().catch(() => ({}));

  if (res.ok && data.ok && data.data) {
    // 🔥 ATUALIZA O STATE COM O QUE VEIO DO BACKEND
    this.holy.config = {
      host: data.data.host,
      port: data.data.port,
      token: data.data.token,
      is_configured: data.data.is_configured,
    };

    this.holy.testOk = true;
    this.holy.testMessage = 'Configuração salva com sucesso';

    setTimeout(() => {
      this.holy.testMessage = '';
    }, 2500);

    await this.holyRefreshStatus();

  } else {
    this.holy.testOk = false;
    this.holy.testMessage = data.message || 'Erro ao salvar';
  }
},

    // ============================================================
    //  Modal de aviso pre-shutdown
    // ============================================================

    /**
     * Verifica se ha algum shutdown ativo proximo do horario (<= 5 min).
     * Se houver, abre o modal de aviso. Chamado periodicamente em polling.
     */
    async _checkUpcomingShutdown() {
      // Recarrega a lista pra pegar agendamentos novos/cancelados externamente.
      await this.loadShutdowns();

      const now = Date.now();
      const thresholdMs = this.WARNING_THRESHOLD_MIN * 60 * 1000;

      // Pega o shutdown ativo mais proximo dentro da janela.
      const upcoming = this.shutdownSchedules
        .filter(s => s.status === 'scheduled')
        .filter(s => !this.warning.dismissedIds.includes(s.id))
        .map(s => ({ ...s, _ts: new Date(s.scheduled_for).getTime() }))
        .filter(s => s._ts > now && (s._ts - now) <= thresholdMs)
        .sort((a, b) => a._ts - b._ts)[0];

      if (!upcoming) {
        // Nada na janela. Se o modal estava aberto pra um agendamento que
        // foi cancelado externamente, fecha.
        if (this.warning.visible &&
            !this.shutdownSchedules.some(s => s.id === this.warning.scheduleId && s.status === 'scheduled')) {
          this._hideWarning();
        }
        return;
      }

      // Se o modal ja esta aberto pra esse mesmo, so atualiza countdown.
      if (this.warning.visible && this.warning.scheduleId === upcoming.id) return;

      this._showWarning(upcoming);
    },

    /**
     * Abre o modal de aviso pra um agendamento especifico.
     *
     * @param {object} schedule Agendamento (com _ts).
     */
    _showWarning(schedule) {
      this.warning.visible = true;
      this.warning.scheduleId = schedule.id;
      this.warning.action = schedule.action;
      this.warning.scheduledFor = schedule.scheduled_for;
      this._tickWarning();

      // Atualiza o countdown a cada segundo.
      if (this._warningTickId) clearInterval(this._warningTickId);
      this._warningTickId = setInterval(() => this._tickWarning(), 1000);

      // Tenta tocar um beep curto via Web Audio (sem depender de arquivo MP3).
      this._playAlertBeep();
    },

    /**
     * Atualiza o texto do countdown (HH:MM:SS) com base em scheduledFor.
     */
    _tickWarning() {
      if (!this.warning.scheduledFor) return;
      const target = new Date(this.warning.scheduledFor).getTime();
      const diff = Math.max(0, target - Date.now());
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      const pad = (n) => String(n).padStart(2, '0');
      this.warning.countdown = `${pad(h)}:${pad(m)}:${pad(s)}`;

      // Se chegou em zero, fecha o modal (o backend ja vai disparar a acao).
      if (diff === 0) this._hideWarning();
    },

    /**
     * Esconde o modal e cancela o ticker.
     */
    _hideWarning() {
      this.warning.visible = false;
      if (this._warningTickId) {
        clearInterval(this._warningTickId);
        this._warningTickId = null;
      }
    },

    /**
     * Toca um beep curto pra chamar atencao quando o modal abre.
     * Usa Web Audio API (zero arquivo externo). Ignora silenciosamente
     * em browsers que nao permitirem audio sem interacao previa.
     */
    _playAlertBeep() {
      try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.value = 880;
        gain.gain.setValueAtTime(0.15, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
        osc.connect(gain).connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.6);
      } catch (e) { /* navegador nao permite audio */ }
    },

    /**
     * Acao do modal: adiar o agendamento por N minutos.
     * Cancela o atual e cria novo.
     *
     * @param {number} minutes
     */
    async postponeWarning(minutes) {
      const id = this.warning.scheduleId;
      if (!id) return;
      const res = await fetch(`/api/shutdown/${id}/postpone?minutes=${minutes}`, {
        method: 'POST',
      });
      if (res.ok) {
        this._hideWarning();
        await this.loadShutdowns();
      } else {
        alert('Falha ao adiar. Tente novamente pela aba Desligamento.');
      }
    },

    /**
     * Acao do modal: cancelar o agendamento (status -> cancelled).
     */
    async cancelWarning() {
      const id = this.warning.scheduleId;
      if (!id) return;
      const res = await fetch(`/api/shutdown/${id}/cancel`, { method: 'POST' });
      if (res.ok) {
        this._hideWarning();
        await this.loadShutdowns();
      }
    },

    /**
     * Acao do modal: fechar e nao mostrar de novo pra esse agendamento.
     */
    dismissWarning() {
      const id = this.warning.scheduleId;
      if (id != null && !this.warning.dismissedIds.includes(id)) {
        this.warning.dismissedIds.push(id);
      }
      this._hideWarning();
    },

    // ============================================================
    //  Helpers genericos
    // ============================================================

    async copy(text, field) {
      try {
        await navigator.clipboard.writeText(text);
        this.copiedField = field;
        setTimeout(() => { this.copiedField = ''; }, 1800);
      } catch (e) { /* clipboard indisponivel */ }
    },

    weekdayName(idx) {
      if (idx === null || idx === undefined) return '-';
      return ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom'][idx];
    },

    async logout() {
      await fetch('/api/auth/logout', { method: 'POST' });
      window.location.href = '/login';
    },

    // ---------- Utilitarios privados ----------

    /**
     * Converte Date para o formato "YYYY-MM-DDTHH:MM" usado pelo
     * <input type="datetime-local">.
     */
    _toDatetimeLocal(d) {
      const pad = (n) => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
             `T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    },

    /**
     * Converte Date para ISO local sem timezone.
     */
    _toLocalIso(d) {
      const pad = (n) => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
             `T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
    },
  };
}
