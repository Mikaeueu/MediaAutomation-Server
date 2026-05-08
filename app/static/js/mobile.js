/**
 * Componente Alpine.js do painel mobile.
 *
 * Funcionalidades: controle de cenas, audio (volumes/mute), hotkeys F1/F3,
 * gravacao do OBS. Tambem mantem o modal de aviso pre-shutdown caso o
 * desktop agende um shutdown enquanto o operador esta no celular.
 *
 * @returns {object}
 */
function mobileApp() {
  const initial =
    (typeof window !== 'undefined' && window.__APP_INITIAL) || {};
  console.log('[MediaServer mobile] init com', initial);

  return {
    tab: 'scenes',

    network: initial.network || {},
    username: initial.username || '',

    // ---------- OBS ----------
    obsStatus: { connected: false, recording: { active: false, timecode: '00:00:00' }, current_scene: null },
    scenes: [],
    audioInputs: [],

    // ---------- Holyrics ----------
    holy: {
    status: {
        connected: false
    },

    config: {
        is_configured: false
    },

    showConfig: false,
    showToken: false,

    versions: [],
    books: [],
    filteredBooks: [],

    availableChapters: [],
    availableVerses: [],

    recent: [],

    error: "",

    form: {
        version: "rc",
        book: "",
        chapter: "",
        verse: ""
    },

    bookSearch: "",

    configForm: {
        host: "",
        port: 8091,  // ✅ corrigido: era 8080
        token: ""
    }
},

    // ---------- Modal de aviso ----------
    WARNING_THRESHOLD_MIN: 5,
    warning: {
      visible: false,
      scheduleId: null,
      action: 'shutdown',
      scheduledFor: null,
      countdown: '',
      dismissedIds: [],
    },
    _warningTickId: null,
    _shutdownPollId: null,
    _obsPollId: null,
    _volumeDebounce: null,

    // ============================================================
    //  Bootstrap
    // ============================================================

    async init() {
      await this.obsRefresh();
      this._obsPollId = setInterval(() => this.obsRefresh(), 5000);

      this._shutdownPollId = setInterval(() => this._checkUpcomingShutdown(), 30 * 1000);
      this._checkUpcomingShutdown();
    },

    // ============================================================
    //  OBS - Cenas / Status / Recording
    // ============================================================

    async obsRefresh() {
      try {
        const res = await fetch('/api/obs/status');
        if (res.ok) this.obsStatus = await res.json();
      } catch (e) { /* offline */ }

      if (this.obsStatus.connected) {
        await this.obsLoadScenes();
      } else {
        this.scenes = [];
        this.audioInputs = [];
      }
    },

    async obsLoadScenes() {
      try {
        const res = await fetch('/api/obs/scenes');
        if (res.ok) {
          const data = await res.json();
          this.scenes = data.scenes || [];
        }
      } catch (e) {}
    },

    async obsSwitchScene(name) {
      const res = await fetch('/api/obs/scenes/activate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      if (res.ok) {
        this.obsStatus.current_scene = name;
      } else {
        const err = await res.json().catch(() => ({}));
        alert('Falha: ' + (err.detail || 'erro'));
      }
    },

    async obsToggleRecording() {
      const res = await fetch('/api/obs/recording/toggle', { method: 'POST' });
      if (res.ok) await this.obsRefresh();
    },

    // ============================================================
    //  OBS - Hotkeys (F1, F3, etc.)
    // ============================================================

    /**
     * Dispara uma hotkey do OBS pelo identificador da tecla.
     *
     * @param {string} keyId Ex: "OBS_KEY_F1", "OBS_KEY_F3".
     */
    async obsHotkey(keyId) {
      const res = await fetch('/api/obs/hotkey/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: keyId }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert('Falha ao acionar atalho: ' + (err.detail || keyId));
      }
    },

    // ============================================================
    //  OBS - Audio (volumes + mute)
    // ============================================================

    async obsLoadAudioInputs() {
      if (!this.obsStatus.connected) return;
      try {
        const res = await fetch('/api/obs/audio/inputs');
        if (res.ok) {
          const data = await res.json();
          this.audioInputs = data.inputs || [];
        }
      } catch (e) {}
    },

    /**
     * Seta volume com debounce de 100ms pra nao spammar o OBS.
     *
     * @param {string} name
     * @param {number|string} volume Multiplicador 0..1.
     */
    obsSetVolume(name, volume) {
      const v = parseFloat(volume);
      if (this._volumeDebounce) clearTimeout(this._volumeDebounce);
      this._volumeDebounce = setTimeout(async () => {
        await fetch('/api/obs/audio/volume', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, volume_mul: v }),
        });
      }, 100);
    },

    async obsMute(name) {
      const res = await fetch('/api/obs/audio/mute/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      if (res.ok) {
        // Atualiza so o input afetado, sem recarregar tudo.
        const data = await res.json();
        const inp = this.audioInputs.find(i => i.name === name);
        if (inp) inp.muted = data.muted;
      }
    },

    // ============================================================
    //  Holyrics (Bíblia / projeção de versículos)
    // ============================================================

    /**
     * Carrega config + livros + versões + recentes ao entrar na aba.
     */
    
    async holyLoad() {

      await this.holyLoadConfig();

      try {
        const res = await fetch('/api/holyrics/meta');
        const metaRes = await res.json();

        const meta = metaRes.data || [];

        this.holy.books = meta.map((book, i) => ({
          id: i + 1,
          abbr: book.abbr,
          name: book.book,
          chapters: book.chapters
        }));

        this.holy.filteredBooks = [...this.holy.books];

      } catch (e) {
        console.error('Erro ao carregar meta:', e);
      }

      if (this.holy.config.is_configured) {
        await Promise.all([
          this.holyLoadVersions(),
          this.holyLoadRecent(),
          this.holyRefreshStatus()
        ]);
      }
    },

async holyLoadConfig() {
  try {
    const res = await fetch('/api/holyrics/config');
    const json = await res.json();

    if (json.ok && json.data) {

      const cfg = json.data;

      this.holy.config = {
        host: cfg.host || this.holy.config.host,
        port: cfg.port || this.holy.config.port,
        token: cfg.token || this.holy.config.token,
        is_configured: cfg.is_configured ?? !!this.holy.config.token,
      };

      this.holy.configForm = {
        host: this.holy.config.host || "",
        port: this.holy.config.port || 8091,  // ✅ corrigido: era 8080
        token: this.holy.config.token || "",
      };

    } else {
      console.warn('Holyrics config inválida, mantendo anterior');
    }

  } catch (e) {
    console.error('Erro ao carregar config Holyrics:', e);
  }
},

    async holyLoadVersions() {
      try {
        const res = await fetch('/api/holyrics/versions');
        const json = await res.json();

        // ✅ corrigido: aceita lista direta ou {versions: [...]}
        const raw = json.data;
        this.holy.versions = Array.isArray(raw)
          ? raw
          : (raw?.versions || []);

      } catch (e) {
        this.holy.versions = [];
      }
    },


    async holyLoadRecent() {
      try {
        const res = await fetch('/api/holyrics/recent');
        const json = await res.json();

        // ✅ corrigido: era json.data?.items — backend retorna lista direta
        this.holy.recent = Array.isArray(json.data) ? json.data : [];

      } catch (e) {
        this.holy.recent = [];
      }
    },

    async holyRefreshStatus() {
      try {
        const res = await fetch('/api/holyrics/status');
        const json = await res.json();

        this.holy.status = json.data || { connected: false };

      } catch (e) {
        this.holy.status = { connected: false };
      }
    },

    async holyTestConfig() {
      this.holy.testMessage = 'Testando...';
      this.holy.testOk = false;

      try {
        const res = await fetch('/api/holyrics/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.holy.configForm),
        });

        const json = await res.json();

        this.holy.testOk = !!json.ok;
        this.holy.testMessage = json.message || (json.ok ? 'OK' : 'Falha');

      } catch (e) {
        this.holy.testOk = false;
        this.holy.testMessage = 'Erro de conexão';
      }
    },

    async holySaveConfig() {
      try {
        const res = await fetch('/api/holyrics/config', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            host: this.holy.configForm.host,
            port: parseInt(this.holy.configForm.port, 10),
            token: this.holy.configForm.token || '',
          }),
        });

        const json = await res.json();

        if (json.ok) {
          this.holy.config = json.data;

          this.holy.testMessage = 'Salvo com sucesso';
          this.holy.testOk = true;

          setTimeout(() => {
            this.holy.testMessage = '';
            this.holy.showConfig = false;
          }, 1200);

          await this.holyLoad();

        } else {
          this.holy.testOk = false;
          this.holy.testMessage = json.message || 'Erro ao salvar';
        }

      } catch (e) {
        this.holy.testOk = false;
        this.holy.testMessage = 'Erro inesperado';
      }
    },

    async holyShowVerse() {
      this.holy.error = '';

      const f = this.holy.form;

      try {
        const res = await fetch('/api/holyrics/verse', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            version: f.version,
            book: f.book,
            chapter: parseInt(f.chapter, 10),
            verse: parseInt(f.verse, 10),
          }),
        });

        const json = await res.json();

        if (res.ok && json.ok) {
          await this.holyLoadRecent();
        } else {
          this.holy.error = json.message || 'Falha ao mostrar versículo';
        }

      } catch (e) {
        this.holy.error = 'Erro de conexão';
      }
    },

    async holyClose() {
      try {
        const res = await fetch('/api/holyrics/close', { method: 'POST' });
        const json = await res.json();

        if (!json.ok) {
          this.holy.error = json.message || 'Falha ao esconder';
        }

      } catch (e) {
        this.holy.error = 'Erro de conexão';
      }
    },

    filterBooks() {

      const q = (this.holy.bookSearch || '')
        .toLowerCase()
        .trim();

      if (!q) {
        this.holy.filteredBooks = [...this.holy.books];
        return;
      }

      this.holy.filteredBooks = this.holy.books.filter(book =>
        (book.name || '')
            .toLowerCase()
            .includes(q)
      );
    },

    updateChapters() {

      const book = this.holy.books.find(
        b => b.abbr === this.holy.form.book
      );

      if (!book) {
        this.holy.availableChapters = [];
        return;
      }

      this.holy.availableChapters = book.chapters.map(
        c => Number(c.chapter)
      );

      this.holy.form.chapter = '';
      this.holy.form.verse = '';
      this.holy.availableVerses = [];
    },
    

    updateVerses() {

      const book = this.holy.books.find(
        b => b.abbr === this.holy.form.book
      );

      if (!book) return;

      const chapterData = book.chapters.find(
        c => Number(c.chapter) === Number(this.holy.form.chapter)
      );

      if (!chapterData) return;

      const totalVerses = Number(chapterData.verses || 0);

      this.holy.availableVerses = Array.from(
        { length: totalVerses },
        (_, i) => i + 1
      );

      this.holy.form.verse = '';
    },


    /**
     * Repete um verso do histórico (preenche form e mostra).
     */
    async holyRepeat(item) {
      this.holy.form = {
        version: item.version,
        book: item.book,
        chapter: item.chapter,
        verse: item.verse,
      };
      await this.holyShowVerse();
    },

    // ============================================================
    //  Modal de aviso pre-shutdown (mantido)
    // ============================================================

    async _checkUpcomingShutdown() {
      let shutdowns = [];
      try {
        const res = await fetch('/api/shutdown');
        if (res.ok) shutdowns = await res.json();
      } catch (e) { return; }

      const now = Date.now();
      const thresholdMs = this.WARNING_THRESHOLD_MIN * 60 * 1000;

      const upcoming = shutdowns
        .filter(s => s.status === 'scheduled')
        .filter(s => !this.warning.dismissedIds.includes(s.id))
        .map(s => ({ ...s, _ts: new Date(s.scheduled_for).getTime() }))
        .filter(s => s._ts > now && (s._ts - now) <= thresholdMs)
        .sort((a, b) => a._ts - b._ts)[0];

      if (!upcoming) {
        if (this.warning.visible) this._hideWarning();
        return;
      }
      if (this.warning.visible && this.warning.scheduleId === upcoming.id) return;
      this._showWarning(upcoming);
    },

    _showWarning(schedule) {
      this.warning.visible = true;
      this.warning.scheduleId = schedule.id;
      this.warning.action = schedule.action;
      this.warning.scheduledFor = schedule.scheduled_for;
      this._tickWarning();
      if (this._warningTickId) clearInterval(this._warningTickId);
      this._warningTickId = setInterval(() => this._tickWarning(), 1000);
      this._playAlertBeep();
    },

    _tickWarning() {
      const target = new Date(this.warning.scheduledFor).getTime();
      const diff = Math.max(0, target - Date.now());
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      const pad = (n) => String(n).padStart(2, '0');
      this.warning.countdown = `${pad(h)}:${pad(m)}:${pad(s)}`;
      if (diff === 0) this._hideWarning();
    },

    _hideWarning() {
      this.warning.visible = false;
      if (this._warningTickId) {
        clearInterval(this._warningTickId);
        this._warningTickId = null;
      }
    },

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
      } catch (e) {}
    },

    async postponeWarning(minutes) {
      const id = this.warning.scheduleId;
      if (!id) return;
      const res = await fetch(`/api/shutdown/${id}/postpone?minutes=${minutes}`, { method: 'POST' });
      if (res.ok) this._hideWarning();
    },

    async cancelWarning() {
      const id = this.warning.scheduleId;
      if (!id) return;
      const res = await fetch(`/api/shutdown/${id}/cancel`, { method: 'POST' });
      if (res.ok) this._hideWarning();
    },

    dismissWarning() {
      const id = this.warning.scheduleId;
      if (id != null && !this.warning.dismissedIds.includes(id)) {
        this.warning.dismissedIds.push(id);
      }
      this._hideWarning();
    },

    // ============================================================
    //  Helpers
    // ============================================================

    formatDateTime(iso) {
      if (!iso) return '';
      const d = new Date(iso);
      if (isNaN(d.getTime())) return iso;
      const pad = (n) => String(n).padStart(2, '0');
      return `${pad(d.getDate())}/${pad(d.getMonth() + 1)} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    },

    async logout() {
      await fetch('/api/auth/logout', { method: 'POST' });
      window.location.href = '/login';
    },
  };
}
