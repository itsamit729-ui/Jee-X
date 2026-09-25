// Service 7: Edge Coins wallet + reward redemption.
import { request } from './api.js'

export const rewardsService = {
  getWallet: () => request('/api/rewards', {}),
  redeem: (payload) => request('/api/rewards/redeem', { method: 'POST', body: payload }),
}
