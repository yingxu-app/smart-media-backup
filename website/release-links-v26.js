(() => {
  const releaseUrl = 'https://github.com/luguanlin20050927/smart-media-backup/releases/download/v1.0.5/YINGXU-macOS-v1.0.5.dmg';
  document.querySelectorAll('a[href^="releases/"]').forEach((link) => { link.href = releaseUrl; });
  document.querySelectorAll('a[href*="-v18.html"],a[href*="-v19.html"],a[href*="-v20.html"],a[href*="-v21.html"],a[href*="-v22.html"],a[href*="-v23.html"]').forEach((link) => {
    link.href = link.getAttribute('href').replace(/-v(?:18|19|20|21|22|23|24|25)\.html/g, '-v26.html');
  });
})();
