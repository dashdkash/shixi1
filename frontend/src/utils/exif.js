/**
 * 图片 EXIF GPS 信息提取工具
 *
 * 从上传图片的 EXIF 标签中读取 GPS 经纬度，
 * 将 DMS（度分秒）格式转为十进制度数。
 *
 * 使用方式：
 *   import { extractGPSFromImage } from "@/utils/exif";
 *   const gps = await extractGPSFromImage(file);
 *   // gps = { latitude: 30.123456, longitude: 120.654321 } 或 null
 */
import EXIF from "exif-js";

/**
 * 将 EXIF GPS DMS（度分秒）数组转为十进制度数
 * @param {Array} dms - [degrees, minutes, seconds] 每项为 { numerator, denominator } 或直接数字
 * @param {string} ref - 方向参考 "N"/"S"/"E"/"W"
 * @returns {number|null}
 */
function dmsToDecimal(dms, ref) {
  if (!dms || dms.length < 3) return null;

  const toNum = (v) => {
    if (typeof v === "number") return v;
    if (v && typeof v === "object" && v.numerator !== undefined) {
      return v.numerator / (v.denominator || 1);
    }
    return Number(v) || 0;
  };

  const d = toNum(dms[0]);
  const m = toNum(dms[1]);
  const s = toNum(dms[2]);
  let decimal = d + m / 60 + s / 3600;

  if (ref === "S" || ref === "W") {
    decimal = -decimal;
  }

  return Math.round(decimal * 1000000) / 1000000;
}

/**
 * 从图片文件中提取 GPS 经纬度
 * @param {File} file - 图片文件对象
 * @returns {Promise<{latitude: number, longitude: number}|null>}
 */
export function extractGPSFromImage(file) {
  return new Promise((resolve) => {
    // 仅支持 JPEG（EXIF 主要在 JPEG 中）
    if (!file || !file.type?.startsWith("image/")) {
      resolve(null);
      return;
    }

    EXIF.getData(file, function () {
      const lat = EXIF.getTag(this, "GPSLatitude");
      const latRef = EXIF.getTag(this, "GPSLatitudeRef") || "N";
      const lng = EXIF.getTag(this, "GPSLongitude");
      const lngRef = EXIF.getTag(this, "GPSLongitudeRef") || "E";

      if (!lat || !lng) {
        resolve(null);
        return;
      }

      const latitude = dmsToDecimal(lat, latRef);
      const longitude = dmsToDecimal(lng, lngRef);

      if (latitude === null || longitude === null) {
        resolve(null);
        return;
      }

      resolve({ latitude, longitude });
    });
  });
}
