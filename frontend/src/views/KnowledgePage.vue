<template>
  <div class="page-container">
    <PageHeader
      :title="$t('knowledge.title')"
      :subtitle="$t('knowledge.subtitle')"
    >
      <template #icon>
        <el-icon><Collection /></el-icon>
      </template>
      <template #extra>
        <el-space>
          <el-button
            v-if="userStore.isSuperuser"
            @click="buildPreset"
          >
            <el-icon><Refresh /></el-icon>
            {{ $t('knowledge.buildPreset') }}
          </el-button>
          <el-button type="primary" @click="showUploadDialog = true">
            <el-icon><Plus /></el-icon>
            {{ $t('knowledge.uploadDoc') }}
          </el-button>
        </el-space>
      </template>
    </PageHeader>

    <!-- Statistics -->
    <div class="stats-grid">
      <StatsCard
        :title="$t('knowledge.statDocCount')"
        :value="stats.document_count"
        :icon="Document"
      />
      <StatsCard
        :title="$t('knowledge.statChunkCount')"
        :value="stats.chunk_count"
        :icon="Collection"
      />
      <StatsCard
        :title="$t('knowledge.statPresetCount')"
        :value="stats.preset_count"
        :icon="Folder"
      />
      <StatsCard
        :title="$t('knowledge.statUploadCount')"
        :value="stats.upload_count"
        :icon="FolderOpened"
      />
    </div>

    <!-- Document List -->
    <SectionCard :title="$t('knowledge.docList')">
      <template #extra>
        <el-button text @click="fetchDocuments">
          <el-icon><Refresh /></el-icon>
          {{ $t('knowledge.refresh') }}
        </el-button>
      </template>

      <EmptyState
        v-if="documents.length === 0 && !loading"
        :title="$t('knowledge.emptyDocs')"
        :description="$t('knowledge.emptyDocsHint')"
      >
        <template #icon>
          <el-icon><Document /></el-icon>
        </template>
      </EmptyState>

      <el-table
        v-else
        :data="documents"
        v-loading="loading"
        stripe
      >
        <el-table-column prop="title" :label="$t('knowledge.colTitle')" />

        <el-table-column :label="$t('knowledge.colSource')" width="140">
          <template #default="{ row }">
            <el-tag :type="row.source_type === 'preset' ? 'success' : 'primary'">
              {{ row.source_type === 'preset' ? $t('knowledge.sourcePreset') : $t('knowledge.sourceUpload') }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="$t('knowledge.colOwner')" width="120">
          <template #default="{ row }">
            <span>{{ row.is_owner ? $t('knowledge.ownerMine') : $t('knowledge.ownerSystem') }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="chunk_count" :label="$t('knowledge.colChunks')" width="100" />

        <el-table-column prop="created_at" :label="$t('knowledge.colCreatedAt')" width="180" />

        <el-table-column :label="$t('knowledge.colAction')" width="120">
          <template #default="{ row }">
            <el-button
              v-if="row.is_owner || userStore.isSuperuser"
              text
              type="danger"
              @click="deleteDocument(row)"
            >
              {{ $t('knowledge.btnDelete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </SectionCard>

    <!-- Search Test -->
    <SectionCard :title="$t('knowledge.searchTest')">
      <div class="search-bar">
        <el-input
          v-model="searchQuery"
          :placeholder="$t('knowledge.searchPlaceholder')"
          clearable
          @keyup.enter="searchKnowledge"
        />
        <el-button
          type="primary"
          :loading="searching"
          @click="searchKnowledge"
        >
          {{ $t('knowledge.searchBtn') }}
        </el-button>
      </div>

      <EmptyState
        v-if="!searchResults.length && !searching"
        :title="$t('knowledge.noSearchResults')"
      />

      <div v-else class="search-results">
        <el-card
          v-for="item in searchResults"
          :key="item.id"
          shadow="never"
          class="search-result-card"
        >
          <h4>{{ item.title }}</h4>
          <p>{{ item.content }}</p>
          <el-tag>{{ item.score?.toFixed(3) }}</el-tag>
        </el-card>
      </div>
    </SectionCard>

    <!-- Upload Dialog -->
    <el-dialog
      v-model="showUploadDialog"
      :title="$t('knowledge.uploadDialogTitle')"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form :model="uploadForm" label-width="90px">
        <el-form-item :label="$t('knowledge.uploadLabelTitle')">
          <el-input
            v-model="uploadForm.title"
            :placeholder="$t('knowledge.uploadTitlePlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('knowledge.uploadLabelSource')">
          <el-radio-group v-model="uploadForm.source_type">
            <el-radio value="upload">{{ $t('knowledge.sourceUpload') }}</el-radio>
            <el-radio v-if="userStore.isSuperuser" value="preset">{{ $t('knowledge.sourcePreset') }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="$t('knowledge.uploadLabelFile')">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            :show-file-list="true"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            accept=".pdf,.txt,.md"
          >
            <el-button type="primary">{{ $t('knowledge.selectFile') }}</el-button>
            <template #tip>
              <div class="upload-tip">{{ $t('knowledge.uploadTip') }}</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="uploading" @click="uploadDocument">
          {{ $t('knowledge.uploadBtn') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { useUserStore } from "@/stores/user";
import request from "@/utils/request";
import { ElMessage, ElMessageBox } from "element-plus";
import { useI18n } from "vue-i18n";
import {
  Plus,
  Refresh,
  Document,
  Collection,
  Folder,
  FolderOpened,
} from "@element-plus/icons-vue";

import PageHeader from "@/components/common/PageHeader.vue";
import SectionCard from "@/components/common/SectionCard.vue";
import StatsCard from "@/components/common/StatsCard.vue";
import EmptyState from "@/components/common/EmptyState.vue";

const { t } = useI18n({ useScope: "global" });
const userStore = useUserStore();

const documents = ref([]);
const loading = ref(false);
const searchQuery = ref("");
const searching = ref(false);
const searchResults = ref([]);
const stats = reactive({
  document_count: 0,
  chunk_count: 0,
  preset_count: 0,
  upload_count: 0,
});

const showUploadDialog = ref(false);
const uploading = ref(false);
const uploadRef = ref();
const selectedFile = ref(null);

const uploadForm = reactive({
  title: "",
  source_type: "upload",
});

async function fetchDocuments() {
  loading.value = true;
  try {
    const res = await request.get("/knowledge/documents");
    documents.value = res.data || [];
  } catch (error) {
    ElMessage.error(t("knowledge.msgFetchFail"));
    console.error(error);
  } finally {
    loading.value = false;
  }
}

async function fetchStats() {
  try {
    const res = await request.get("/knowledge/stats");
    Object.assign(stats, res);
  } catch (error) {
    console.error(error);
  }
}

async function buildPreset() {
  try {
    await ElMessageBox.confirm(
      t("knowledge.buildConfirmMsg"),
      t("common.warning"),
      { type: "warning" }
    );
    const res = await request.post("/knowledge/build");
    ElMessage.success(res.message);
    fetchDocuments();
    fetchStats();
  } catch (error) {
    if (error !== "cancel") {
      ElMessage.error(t("knowledge.msgBuildFail"));
    }
  }
}

function handleFileChange(file) {
  selectedFile.value = file.raw;
}

function handleFileRemove() {
  selectedFile.value = null;
}

async function uploadDocument() {
  if (!selectedFile.value) {
    ElMessage.warning(t("knowledge.msgNoFile"));
    return;
  }

  const formData = new FormData();
  formData.append("file", selectedFile.value);
  if (uploadForm.title.trim()) {
    formData.append("title", uploadForm.title.trim());
  }
  formData.append("source_type", uploadForm.source_type);

  uploading.value = true;
  try {
    const res = await request.post("/knowledge/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    ElMessage.success(t("knowledge.msgUploadSuccess", { count: res.chunk_count }));
    showUploadDialog.value = false;
    uploadForm.title = "";
    uploadForm.source_type = "upload";
    selectedFile.value = null;
    uploadRef.value?.clearFiles();
    await fetchDocuments();
    await fetchStats();
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t("knowledge.msgUploadFail"));
  } finally {
    uploading.value = false;
  }
}

async function deleteDocument(row) {
  try {
    await ElMessageBox.confirm(
      t("knowledge.deleteConfirmMsg", { title: row.title }),
      t("knowledge.deleteConfirmTitle"),
      { type: "warning" }
    );
    await request.delete(`/knowledge/documents/${row.id}`);
    ElMessage.success(t("knowledge.msgDeleteSuccess"));
    await fetchDocuments();
    await fetchStats();
  } catch (error) {
    if (error !== "cancel") {
      ElMessage.error(t("knowledge.msgDeleteFail"));
    }
  }
}

async function searchKnowledge() {
  if (!searchQuery.value.trim()) {
    ElMessage.warning(t("knowledge.msgNoQuery"));
    return;
  }
  searching.value = true;
  try {
    const res = await request.post("/knowledge/search", {
      query: searchQuery.value,
      top_k: 5,
    });
    searchResults.value = res.results || [];
  } catch (error) {
    ElMessage.error(t("knowledge.msgSearchFail"));
  } finally {
    searching.value = false;
  }
}

onMounted(() => {
  fetchDocuments();
  fetchStats();
});
</script>

<style scoped lang="scss">
@use "@/assets/styles/variables.scss" as *;

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: $spacing-lg;
  margin-bottom: $spacing-xl;
}

.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: $spacing-lg;

  .el-input {
    flex: 1;
  }
}

.search-results {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.search-result-card {
  h4 {
    margin: 0 0 8px;
    font-size: 15px;
    color: #303133;
  }
  p {
    margin: 0 0 8px;
    font-size: 13px;
    color: #606266;
    line-height: 1.6;
  }
}

.upload-tip {
  margin-top: $spacing-xs;
  font-size: 12px;
  color: $text-secondary;
}

:deep(.el-upload) {
  width: 100%;
}

:deep(.el-upload .el-button) {
  width: 100%;
}

:deep(.el-table) {
  border-radius: $border-radius-md;
}

:deep(.el-dialog) {
  border-radius: $border-radius-lg;
}

:deep(.el-form-item:last-child) {
  margin-bottom: 0;
}

:deep(.el-tag) {
  text-transform: capitalize;
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
