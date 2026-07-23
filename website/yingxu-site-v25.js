/* One language state, original homepage dropdowns, and one brand icon for YINGXU v25. */
(() => {
  const LANGUAGE_KEY = 'yingxu-language';
  const legacyKeys = ['smb-lang', 'smb_lang', 'smbLang', 'smb_faq_lang', 'lang'];
  const normalize = value => value === 'en' ? 'en' : 'zh';
  const getLanguage = () => {
    const stored = localStorage.getItem(LANGUAGE_KEY);
    if (stored) return normalize(stored);
    return legacyKeys.some(key => localStorage.getItem(key) === 'en') ? 'en' : 'zh';
  };
  const storeLanguage = language => {
    const value = normalize(language);
    localStorage.setItem(LANGUAGE_KEY, value);
    localStorage.setItem('smb-lang', value);
    localStorage.setItem('smb_lang', value);
    localStorage.setItem('smbLang', value);
    localStorage.setItem('smb_faq_lang', value === 'en' ? 'en' : 'zh-CN');
    localStorage.setItem('lang', value);
    document.documentElement.lang = value === 'en' ? 'en' : 'zh-CN';
    return value;
  };

  // Ensure every page begins from exactly the same language before its own UI runs.
  storeLanguage(getLanguage());

  const style = document.createElement('style');
  style.textContent = `
    .brand-mark{background-image:url("yingxu-pwa-icon.svg")!important;background-position:center!important;background-size:72%!important;background-repeat:no-repeat!important}
    .brand-mark::before,.brand-mark::after{content:none!important}
    .nav-links > a:not(.btn){display:inline-flex;align-items:center;min-height:38px;padding:0 4px;color:var(--text-dim,var(--muted,#aab0bc));text-decoration:none;font:inherit;transition:color .18s ease}
    .nav-links > a:not(.btn):hover{color:var(--text,#f4f6f8)}
    .nav-links [data-yingxu-language-toggle]{min-width:50px;min-height:38px;padding:0 13px;border:1px solid var(--border,#2c3238);border-radius:12px;background:rgba(255,255,255,.025);color:var(--text-dim,var(--muted,#aab0bc));font:inherit;cursor:pointer}
  `;
  document.head.appendChild(style);

  const englishText = {
    '不是拷贝':'Not just copying', '是归处':'A place for every file',
    '向下滚动，看看一张混乱的卡片如何变成可验证、可检索的作品库。':'Scroll to see how a messy card becomes a verified, searchable archive.',
    '先读懂':'First, understand', '这一张卡。':'this card.',
    '读取设备、拍摄时间与媒体类型。面对婚礼、航拍、产品和街头素材，先让每一批文件拥有可理解的上下文。':'Read the device, capture time, and media type. Give every wedding, aerial, product, and street shoot useful context first.',
    '把混乱':'Send the mess', '送到正确的地方':'to the right place',
    '按设备、项目和媒体类型归档；备份到电脑、外置盘或已挂载的 NAS。你命名一次，后面的路径由影序接手。':'Archive by device, project, and media type; back up to your Mac, external drive, or mounted NAS. Name it once — YINGXU handles the path after that.',
    '不是应该备了':'Not “it should be backed up”', '而是已经确认':'but “it is confirmed”',
    '每一次复制都留下校验记录与备份历史。以后找素材时，不再靠回忆翻硬盘，而是从清晰的归档线索开始。':'Every copy leaves a verification record and history. Find work through clear archive context, not by searching drives from memory.',
    '素材安全':'Media safety', '要能被证明':'should be provable',
    '影序不把“放心”写成口号，而是把每一步做成可以检查的记录。':'YINGXU does not promise peace of mind — it makes every step inspectable.',
    '原卡不动':'The source card stays untouched', '影序读取并复制素材，不重命名、不修改、不删除 SD 卡中的原始文件。':'YINGXU reads and copies media. It never renames, changes, or deletes originals on your SD card.',
    '复制后校验':'Verify after copying', '通过 SHA256 对照源文件与目标文件，明确告诉你这次备份是否完整。':'SHA256 compares source and destination files, so you know whether this backup is complete.',
    '留下一条记录':'Leave a trace', '设备、项目、目标位置和完成状态写入历史，下一次找回不再从“我记得”开始。':'Device, project, destination, and completion state are written to history, so recovery never starts with “I think I remember.”',
    '不管从哪拍':'Whatever you shoot with', '都回到同一套秩序':'it returns to one system',
    '影序不是只服务一种相机，它服务的是一位创作者完整而复杂的工作流。':'YINGXU is not for one camera; it is for a creator’s complete, complex workflow.',
    '相机素材':'Camera media', '人物、婚礼、产品、街头与风景。按设备和项目，保留原始拍摄语境。':'People, weddings, products, streets, and landscapes — keep the original shooting context by device and project.',
    '无人机航拍':'Drone footage', '把飞行素材从存储卡带回项目目录，不再和地面机位混在一起。':'Bring aerial footage from the card into the project folder, never mixed with ground-camera media.',
    '稳定器与第一视角':'Gimbal and first-person media', '视频、音频与照片分开归档，为剪辑和检索留下清晰入口。':'Archive video, audio, and photos separately for a clear editing and search starting point.',
    '先在桌面':'Start on desktop', '把流程跑顺':'and get the workflow right',
    '桌面端是影序的完整备份工作台；移动端会在能力真正可用后再开放下载。':'Desktop is YINGXU’s complete backup workstation. Mobile downloads will arrive only when the capability is genuinely ready.',
    '插卡识别、项目归档、校验与历史记录，面向 Mac 创作者的完整工作流。':'Card detection, project archiving, verification, and history — a complete workflow for Mac creators.',
    '下载 macOS v1.0.4 →':'Download macOS v1.0.4 →',
    '核心代码已适配；正式 .exe 正在等待 Windows 环境构建与验证，不提供未验证的下载。':'Core code is ready; the official .exe awaits a verified Windows build. No unverified download is offered.',
    '查看发布状态 →':'View release status →',
    '无需安装商店 App。手机与桌面端同一 Wi‑Fi 后，扫码配对即可把素材线索直接接力到当前电脑。':'No app store install required. On the same Wi-Fi, scan to pair and hand media context directly to this desktop.',
    '打开移动工作台 →':'Open mobile workspace →',
    '影序正在':'YINGXU is', '和摄影师一起长大':'growing with photographers',
    '没有伪造的好评，只有真实的工作流难题。你的问题会直接进入开发清单；愿意进一步说明时，也可以写邮件给作者。':'No fabricated reviews — only real workflow problems. Your feedback goes directly into the development list; you can also email the creator.',
    '你最希望影序先解决什么素材问题？':'What media problem should YINGXU solve first?',
    '草稿只保存在当前浏览器；也可以公开提交，让其他摄影师一起讨论。':'Drafts stay only in this browser. You can also share them publicly for other photographers to discuss.',
    '邮件反馈':'Email feedback', '查看共创墙与公开建议 →':'View co-creation wall and public suggestions →',
    '先把话':'Let’s make this', '说清楚':'clear first',
    '哪些已经做到，哪些正在构建，影序会在这里如实说明。':'YINGXU states plainly what is ready and what is still being built.',
    '影序现在能做什么？':'What can YINGXU do now?',
    '当前桌面端围绕 SD 卡检测、媒体扫描、按设备 / 项目 / 类型整理、复制、SHA256 校验和历史记录构建。百度网盘与 AI 命名需由用户自行配置对应服务。':'The desktop app supports SD-card detection, media scanning, sorting by device/project/type, copying, SHA256 verification, and history. Cloud and AI naming services require your own configuration.',
    '它会删除或修改我的原片吗？':'Will it delete or modify my originals?',
    '不会。影序的基本原则是保留原卡文件，只执行复制和校验。任何后续的筛选能力都应以“待确认”形式呈现，而不是自动删除。':'No. YINGXU preserves source-card files and only copies and verifies. Any future culling is presented for review, never deleted automatically.',
    '手机端什么时候可以下载？':'When can I download the mobile version?',
    'Android 一键备份方向正在规划与构建。iPhone / iPad 受系统分发和文件访问限制，第一阶段会优先提供网页工作台；未上线前不会提供虚假的下载入口。':'One-tap Android backup is planned and in development. iPhone and iPad have distribution and file-access limits, so the web workspace comes first; no fake download will be offered.',
    '影序免费吗？':'Is YINGXU free?',
    '核心桌面功能以免费、开源为目标。未来如果出现云服务或高级 AI 能力，将明确作为可选功能，不影响基础备份与整理。':'Core desktop features aim to remain free and open source. Future cloud or advanced AI features will be clearly optional and will not affect basic backup and organization.',
    '我是普通摄影师，也能参与改进吗？':'Can a regular photographer help improve it?',
    '可以。影序会建设公开的共创墙，收集真实素材管理难题，并公开记录哪些建议正在处理、哪些已经完成。':'Yes. YINGXU’s public co-creation wall collects real media-management problems and tracks what is being worked on and completed.',
    '从下一张卡':'Start with', '开始整理':'your next card',
    '影序首先服务桌面工作流。下载后，插卡、填一次项目名，然后把剩下的交给可检查的备份记录。':'YINGXU begins with desktop workflows. Download it, insert a card, name the project once, then let inspectable backup records handle the rest.',
    '下载':'Download', '查看状态':'View status', '源代码':'Source code', '查看':'View', '发布包准备中':'Release package in preparation',
    '安装':'Install', '然后开始归档':'then start archiving',
    '影序优先服务本地工作流；你的素材、路径和历史都由你自己掌握。':'YINGXU prioritizes local workflows: your media, paths, and history stay in your hands.',
    '下载 .dmg 并拖入 Applications':'Download the .dmg and drag it into Applications', '从启动台打开影序':'Open YINGXU from Launchpad',
    '首次如出现系统提示：前往「系统设置 → 隐私与安全性」选择仍要打开':'If macOS warns on first launch: System Settings → Privacy & Security → Open Anyway',
    '也可以按住 Control 点击 App 后选择「打开」':'Or Control-click the app and choose Open',
    '完整性校验':'Integrity check', '下载后，在终端运行':'After download, run in Terminal', '确认结果与下载页公布的 SHA-256 一致':'Confirm that it matches the SHA-256 published on the download page',
    '更新日志':'Changelog', '隐私政策':'Privacy', '关于':'About', '联系作者':'Contact creator'
  };

  const replaceText = node => {
    const raw = node.nodeValue;
    const trimmed = raw.trim();
    const next = englishText[trimmed];
    if (!next) return;
    node.nodeValue = raw.replace(trimmed, next);
  };
  const translateHome = language => {
    if (language !== 'en') return;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(replaceText);
    const h1 = document.querySelector('.hero-content h1');
    if (h1) h1.innerHTML = 'Every card<br><span class="gradient-text">has a place</span>';
    const map = [
      ['[data-journey-label]', 'Camera recognized'], ['[data-journey-subtitle]', 'Ready to remove the card'],
      ['[data-story-status]', 'Scanning'], ['[data-story-meta]', 'Device & media'],
      ['[data-story-title]', 'Understanding this card'], ['[data-story-copy]', 'Reading source, capture context, and file types.']
    ];
    map.forEach(([selector, text]) => { const element = document.querySelector(selector); if (element) element.textContent = text; });
    const input = document.querySelector('#feedback-draft');
    if (input) input.placeholder = 'For example: after a wedding, I forget which of two cards has already been backed up…';
  };

  const renderNavigation = language => {
    const nav = document.querySelector('.nav-links');
    if (!nav) return;
    const english = language === 'en';
    nav.innerHTML = `
      <a href="index.html">${english ? 'Home' : '主页'}</a>
      <a href="guide-v24.html">${english ? 'Guide' : '导览'}</a>
      <a href="download-v24.html">${english ? 'Download' : '下载'}</a>
      <button class="lang-btn" type="button" data-yingxu-language-toggle aria-label="${english ? 'Switch to Chinese' : '切换到英文'}">${english ? '中' : 'EN'}</button>
      <a class="btn nav-gh" href="https://github.com/luguanlin20050927/smart-media-backup" target="_blank" rel="noopener noreferrer">GitHub</a>`;
    const toggle = nav.querySelector('[data-yingxu-language-toggle]');
    toggle.addEventListener('click', () => {
      storeLanguage(language === 'en' ? 'zh' : 'en');
      window.location.reload();
    });
  };

  document.addEventListener('DOMContentLoaded', () => {
    // Child-page scripts finish their own initial render first; this canonical layer then wins.
    window.setTimeout(() => {
      const language = storeLanguage(getLanguage());
      const homepage = document.querySelector('.brand-shell');
      // The homepage deliberately retains its richer original dropdown navigation.
      // All secondary pages keep the compact unified navigation.
      if (homepage) {
        document.querySelectorAll('[data-lang-switch]').forEach(button => {
          button.addEventListener('click', () => {
            const next = storeLanguage(button.dataset.langSwitch);
            // The source markup is Chinese. Reload once when returning to Chinese
            // so no translated text nodes from the English view can remain.
            if (next === 'zh') window.location.reload();
            else window.setTimeout(() => translateHome(next), 0);
          });
        });
        translateHome(language);
      } else {
        renderNavigation(language);
      }

      // Scroll animation writes a few status strings after the initial render.
      if (language === 'en' && homepage) {
        const observer = new MutationObserver(records => records.forEach(record => {
          if (record.type === 'characterData') replaceText(record.target);
          record.addedNodes.forEach(node => { if (node.nodeType === Node.TEXT_NODE) replaceText(node); });
        }));
        observer.observe(document.body, { childList: true, subtree: true, characterData: true });
      }
    }, 0);
  });
})();
