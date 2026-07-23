/* Shared branding, navigation, and language state for YINGXU v23. */
(() => {
  const key = 'yingxu-language';
  const getLanguage = () => localStorage.getItem(key) === 'en' ? 'en' : 'zh';
  const storeLanguage = (language) => {
    const zh = language !== 'en';
    localStorage.setItem(key, zh ? 'zh' : 'en');
    localStorage.setItem('smb-lang', zh ? 'zh' : 'en');
    localStorage.setItem('smb_lang', zh ? 'zh' : 'en');
    localStorage.setItem('smbLang', zh ? 'zh' : 'en');
    localStorage.setItem('smb_faq_lang', zh ? 'zh-CN' : 'en');
    localStorage.setItem('lang', zh ? 'zh' : 'en');
    document.documentElement.lang = zh ? 'zh-CN' : 'en';
  };

  storeLanguage(getLanguage());
  const style = document.createElement('style');
  style.textContent = '.brand-mark{background-image:url("yingxu-pwa-icon.svg")!important;background-position:center!important;background-size:72%!important;background-repeat:no-repeat!important}.brand-mark::before,.brand-mark::after{content:none!important}';
  document.head.appendChild(style);

  document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.brand-shell')) return; // Homepage keeps its richer navigation.
    window.setTimeout(() => {
      const nav = document.querySelector('.nav-links');
      if (!nav) return;
      const english = getLanguage() === 'en';
      nav.innerHTML = `
        <a href="index.html">${english ? 'Home' : '主页'}</a>
        <a href="guide-v23.html">${english ? 'Guide' : '导览'}</a>
        <a href="download-v23.html">${english ? 'Download' : '下载'}</a>
        <button class="lang-btn" type="button" data-yingxu-language-toggle>${english ? '中' : 'EN'}</button>
        <a class="btn" href="https://github.com/luguanlin20050927/smart-media-backup" target="_blank" rel="noopener noreferrer">GitHub</a>`;
      const toggle = nav.querySelector('[data-yingxu-language-toggle]');
      toggle.addEventListener('click', () => {
        storeLanguage(getLanguage() === 'en' ? 'zh' : 'en');
        window.location.reload();
      });
    }, 0);
  });

  // The homepage uses a language dropdown rather than the shared child-page button.
  // Mirror its visible choices into the same persistent key after its own handler runs.
  document.addEventListener('click', (event) => {
    const label = (event.target.textContent || '').trim();
    if (label === 'English') window.setTimeout(() => storeLanguage('en'), 0);
    if (label === '中文') window.setTimeout(() => storeLanguage('zh'), 0);
  });
})();
