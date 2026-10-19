App({
  onHide() {
    const pages = getCurrentPages();
    const currentPage = pages[pages.length - 1];
    if (currentPage && typeof currentPage.onAppHide === "function") {
      currentPage.onAppHide();
    }
  },
  globalData: {
    productName: "影序 Pocket Mini Program"
  }
});
