<template>
  <div class="knowledge-page">
    <PageHeader :title="$t('page.knowledge.title')" :subtitle="$t('page.knowledge.description')">
      <template #extra>
        <el-button type="primary" @click="showUploadDialog = true">
          <el-icon><Upload /></el-icon>
          {{ $t('knowledge.upload') }}
        </el-button>
        <el-button @click="handleBuildPreset" :loading="building">
          <el-icon><SetUp /></el-icon>
          {{ $t('knowledge.buildPreset') }}
        </el-button>
      </template>
    </PageHeader>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <StatsCard
        :title="$t('knowledge.stats.documents')"
        :value="stats.total_documents ?? 0"
        icon="📄"
      />
      <StatsCard
        :title="$t('knowledge.stats.chunks')"
        :value="stats.total_chunks ?? 0"
        icon="🧩"
      />
      <StatsCard
        :title="$t('knowledge.stats.sources')"
        :value="stats.sources?.length ?? 0"
        icon="📚"
      />
    </div>

    <!-- 文档列表 + 检索测试 -->
    <div class="knowledge-content">
      <!-- 文档列表 -->
      <SectionCard :title="$t('knowledge.documentList')">
        <template #extra>
          <el-button size="small" @click="fetchDocuments">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </template>

        <el-table :data="documents" v-loading="loadingDocs" stripe>
          <el-table-column prop="filename" :label="$t('knowledge.fileName')" min-width="200" />
          <el-table-column prop="source" :label="$t('knowledge.source')" width="120" />
          <el-table-column prop="chunk_count" :label="$t('knowledge.chunks')" width="100" align="center" />
          <el-table-column prop="created_at" :label="$t('knowledge.createdAt')" width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column :label="$t('knowledge.actions')" width="100" align="center">
            <template #default="{ row }">
              <el-button
                type="danger"
                size="small"
                text
                @click="handleDelete(row)"
              >
                {{ $t('knowledge.delete') }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <EmptyState
          v-if="!loadingDocs && documents.length === 0"
          :title="$t('knowledge.empty')"
          :description="$t('knowledge.emptyDesc')"
        >
          <template #action>
            <el-button type="primary" @click="showUploadDialog = true">
              {{ $t('knowledge.uploadFirst') }}
            </el-button>
          </template>
        </EmptyState>
      </SectionCard>

      <!-- 检索测试 -->
      <SectionCard :title="$t('knowledge.searchTest')">
        <div class="search-box">
          <el-input
            v-model="searchQuery"
            :placeholder="$t('knowledge.searchPlaceholder')"
            @keyup.enter="handleSearch"
            clearable
          >
            <template #append>
              <el-button @click="handleSearch" :loading="searching">
                <el-icon><Search /></el-icon>
              </el-button>
            </template>
          </el-input>
          <el-input-number
            v-model="topK"
            :min="1"
            :max="20"
            :step="1"
            size="small"
            controls-position="right"
            style="width: 100px; margin-left: 8px"
          />
        </div>

        <div v-if="searchResults.length > 0" class="search-results">
          <div v-for="(item, idx) in searchResults" :key="idx" class="result-item">
            <div class="result-header">
              <span class="result-source">{{ item.source || item.filename }}</span>
              <el-tag size="small" type="info">
                {{ $t('knowledge.score') }}: {{ (item.score ?? 0).toFixed(3) }}
              </el-tag>
            </div>
            <div class="result-content">{{ item.content }}</div>
          </div>
        </div>

        <EmptyState
          v-if="searched && searchResults.length === 0"
          :title="$t('knowledge.noResults')"
          description=""
        />
      </SectionCard>
    </div>

    <!-- 上传对话框 -->
    <el-dialog
      v-model="showUploadDialog"
      :title="$t('knowledge.uploadTitle')"
      width="500px"
    >
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :on-change="handleFileChange"
        :file-list="uploadFileList"
        accept=".md,.txt,.pdf,.docx"
        multiple
        drag
      >
        <el-icon class="el-icon--upload"><Upload /></el-icon>
        <div class="el-upload__text">
          {{ $t('knowledge.uploadHint') }}
        </div>
        <template #tip>
          <div class="el-upload__tip">
            {{ $t('knowledge.uploadTip') }}
          </div>
        </template>
      </el-upload>

      <template #footer>
        <el-button @click="showUploadDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button
          type="primary"
          @click="handleUpload"
          :loading="uploading"
          :disabled="uploadFileList.length === 0"
        >
          {{ $t('knowledge.uploadBtn') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Upload,
  SetUp,
  Refresh,
  Search,
} from "@element-plus/icons-vue";
import PageHeader from "@/components/common/PageHeader.vue";
import SectionCard from "@/components/common/SectionCard.vue";
import StatsCard from "@/components/common/StatsCard.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import {
  listDocumentsApi,
  uploadDocumentApi,
  deleteDocumentApi,
  searchKnowledgeApi,
  getKnowledgeStatsApi,
  buildPresetApi,
} from "@/api/knowledge";

// ── 状态 ──
const documents = ref([]);
const stats = reactive({ total_documents: 0, total_chunks: 0, sources: [] });
const loadingDocs = ref(false);
const searching = ref(false);
const searched = ref(false);
const uploading = ref(false);
const building = ref(false);

const searchQuery = ref("");
const searchResults = ref([]);
const topK = ref(5);

const showUploadDialog = ref(false);
const uploadRef = ref(null);
const uploadFileList = ref([]);

// ── 方法 ──

async function fetchDocuments() {
  loadingDocs.value = true;
  try {
    const res = await listDocumentsApi();
    // 后端返回 {data: [...]} 格式
    documents.value = Array.isArray(res?.data) ? res.data : Array.isArray(res) ? res : [];
  } catch {
    // 静默
  } finally {
    loadingDocs.value = false;
  }
}

async function fetchStats() {
  try {
    const res = await getKnowledgeStatsApi();
    if (res) {
      // 后端返回 {document_count, chunk_count, preset_count, upload_count}
      stats.total_documents = res.document_count ?? res.total_documents ?? 0;
      stats.total_chunks = res.chunk_count ?? res.total_chunks ?? 0;
      stats.sources = res.sources ?? [];
    }
  } catch {
    // 静默
  }
}

function handleFileChange(file, fileList) {
  uploadFileList.value = fileList;
}

async function handleUpload() {
  if (uploadFileList.value.length === 0) return;
  uploading.value = true;
  try {
    for (const f of uploadFileList.value) {
      const formData = new FormData();
      formData.append("file", f.raw);
      await uploadDocumentApi(formData);
    }
    ElMessage.success("上传成功");
    showUploadDialog.value = false;
    uploadFileList.value = [];
    fetchDocuments();
    fetchStats();
  } catch (err) {
    ElMessage.error("上传失败: " + (err.response?.data?.detail || err.message));
  } finally {
    uploading.value = false;
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm("确定删除此文档？", "提示", { type: "warning" });
    await deleteDocumentApi(row.id);
    ElMessage.success("已删除");
    fetchDocuments();
    fetchStats();
  } catch {
    // 取消或失败
  }
}

async function handleSearch() {
  if (!searchQuery.value.trim()) return;
  searching.value = true;
  searched.value = false;
  try {
    const res = await searchKnowledgeApi(searchQuery.value, topK.value);
    // 后端返回 {query, results: [...]}
    searchResults.value = Array.isArray(res?.results) ? res.results : Array.isArray(res) ? res : [];
  } catch {
    searchResults.value = [];
  } finally {
    searching.value = false;
    searched.value = true;
  }
}

async function handleBuildPreset() {
  try {
    await ElMessageBox.confirm("将构建预置知识文档索引，是否继续？", "提示");
    building.value = true;
    await buildPresetApi();
    ElMessage.success("预置索引构建完成");
    fetchDocuments();
    fetchStats();
  } catch {
    // 取消或失败
  } finally {
    building.value = false;
  }
}

function formatDate(str) {
  if (!str) return "-";
  try {
    return new Date(str).toLocaleString();
  } catch {
    return str;
  }
}

onMounted(() => {
  fetchDocuments();
  fetchStats();
});
</script>

<style lang="scss" scoped>
.knowledge-page {
  max-width: 1100px;
  margin: 0 auto;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: $spacing-md;
  margin-bottom: $spacing-lg;
}

.knowledge-content {
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
}

.search-box {
  display: flex;
  align-items: center;
  margin-bottom: $spacing-md;
}

.search-results {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.result-item {
  padding: $spacing-sm $spacing-md;
  background: #f9f9f9;
  border: 1px solid #eee;
  border-radius: $border-radius-md;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-xs;

  .result-source {
    font-weight: 500;
    font-size: 13px;
    color: $text-primary;
  }
}

.result-content {
  font-size: 13px;
  color: $text-regular;
  line-height: 1.6;
  white-space: pre-wrap;
}
</style>
