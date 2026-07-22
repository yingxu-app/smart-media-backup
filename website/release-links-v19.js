(() => {
  const releaseUrl = 'https://github.com/luguanlin20050927/smart-media-backup/releases/download/v1.0.1/YINGXU-macOS-v1.0.1.dmg';

  document.querySelectorAll('a[href^="releases/"]').forEach((link) => {
    link.href = releaseUrl;
  });

  document.querySelectorAll('a[href*="-v18.html"]').forEach((link) => {
    link.href = link.getAttribute('href').replace('-v18.html', '-v19.html');
  });
})();
