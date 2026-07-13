/**
 * 权限工具函数
 * 统一判断用户是否为管理员
 */

/**
 * 判断用户是否为管理员
 * @param {Object} user - 用户对象
 * @returns {boolean}
 */
export function isAdmin(user) {
  if (!user) return false;
  if (user.is_superuser) return true;
  if (user.roles && Array.isArray(user.roles) && user.roles.includes('admin')) return true;
  return false;
}
