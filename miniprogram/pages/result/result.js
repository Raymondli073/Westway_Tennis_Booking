Page({
  data: {
    icon:  '✅',
    title: '',
    body:  '',
    type:  'success',
  },

  onLoad(options) {
    this.setData({
      icon:  decodeURIComponent(options.icon  || '✅'),
      title: decodeURIComponent(options.title || ''),
      body:  decodeURIComponent(options.body  || ''),
      type:  options.type || 'success',
    })
  },

  goHome() {
    wx.switchTab ? wx.navigateBack({ delta: 1 }) : wx.redirectTo({ url: '/pages/index/index' })
  }
})
