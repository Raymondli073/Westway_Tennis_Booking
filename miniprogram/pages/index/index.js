const app = getApp()

Page({
  data: {
    email:   '',
    loading: false,
    focused: false,
    count:   0,
  },

  onLoad() {
    this.fetchStats()
  },

  onShow() {
    this.fetchStats()
  },

  fetchStats() {
    wx.request({
      url: `${app.globalData.apiBase}/api/stats`,
      method: 'GET',
      success: (res) => {
        if (res.data && typeof res.data.count === 'number') {
          this.setData({ count: res.data.count })
        }
      },
      fail: () => {} // 静默失败，不影响主流程
    })
  },

  onEmailInput(e) {
    this.setData({ email: e.detail.value })
  },

  onFocus()  { this.setData({ focused: true  }) },
  onBlur()   { this.setData({ focused: false }) },

  onSubscribe() {
    const email = this.data.email.trim()

    if (!email) {
      wx.showToast({ title: '请输入邮箱地址', icon: 'none' })
      return
    }

    const emailRE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRE.test(email)) {
      wx.showToast({ title: '邮箱格式不正确', icon: 'none' })
      return
    }

    this.setData({ loading: true })

    wx.request({
      url: `${app.globalData.apiBase}/api/subscribe`,
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: { email },
      success: (res) => {
        const { ok, code, message, count } = res.data

        if (code === 'already_subscribed') {
          wx.navigateTo({
            url: `/pages/result/result?icon=ℹ️&title=已订阅&body=${encodeURIComponent('该邮箱已在订阅列表中。')}&type=info`
          })
          return
        }

        if (ok) {
          if (typeof count === 'number') this.setData({ count })
          wx.navigateTo({
            url: `/pages/result/result?icon=✅&title=订阅成功&body=${encodeURIComponent(message)}&type=success`
          })
          this.setData({ email: '' })
        } else {
          wx.showToast({ title: message || '订阅失败，请重试', icon: 'none', duration: 2500 })
        }
      },
      fail: () => {
        wx.showToast({ title: '网络错误，请检查连接', icon: 'none' })
      },
      complete: () => {
        this.setData({ loading: false })
      }
    })
  }
})
