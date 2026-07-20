<template>
  <div class="page-container">
    <PageHeader
      title="知识库"
      subtitle="管理 AI 助手使用的知识文档。"
    >
        <template #icon>
            <el-icon><Collection /></el-icon>
        </template>
      <template #extra>
        <el-space>
          <el-button @click="buildPreset">
            <el-icon>
              <Refresh />
            </el-icon>
            构建预置知识库
          </el-button>

          <el-button
            type="primary"
            @click="showUploadDialog = true"
          >
            <el-icon>
              <Plus />
            </el-icon>
            上传文档
          </el-button>
        </el-space>
      </template>
    </PageHeader>

    <!-- ========================= -->
    <!-- Statistics -->
    <!-- ========================= -->

    <div class="stats-grid">
        <StatsCard
            title="文档数量"
            :value="stats.document_count"
            :icon="Document"
        />

        <StatsCard
            title="知识片段"
            :value="stats.chunk_count"
            :icon="Collection"
        />

        <StatsCard
            title="预置文档"
            :value="stats.preset_count"
            :icon="Folder"
        />

        <StatsCard
            title="上传文档"
            :value="stats.upload_count"
            :icon="FolderOpened"
        />
    </div>

    <!-- ========================= -->
    <!-- Document List -->
    <!-- ========================= -->

    <SectionCard title="知识文档">
      <template #extra>
        <el-button
          text
          @click="fetchDocuments"
        >
          <el-icon>
            <Refresh />
          </el-icon>
          刷新
        </el-button>
      </template>

      <EmptyState
        v-if="documents.length === 0"
        title="暂无知识文档"
        description="上传 PDF、TXT 或 Markdown 文档，或者点击“构建预置知识库”。"
      >
        <template #icon>
          <el-icon>
            <Document />
          </el-icon>
        </template>
      </EmptyState>

      <el-table
        v-else
        :data="documents"
        v-loading="loading"
        stripe
      >
        <el-table-column
          prop="title"
          label="标题"
        />

        <el-table-column
          label="来源"
          width="120"
        >
          <template #default="{ row }">
            <el-tag
              :type="row.source_type === 'preset'
                ? 'success'
                : 'primary'"
            >
              {{ row.source_type === "preset"
                ? "系统预置"
                : "用户上传"  }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column
          prop="chunk_count"
          label="片段"
          width="100"
        />

        <el-table-column
          prop="created_at"
          label="创建时间"
          width="180"
        />

        <el-table-column
          label="操作"
          width="120"
        >
          <template #default="{ row }">
            <el-button
              text
              type="danger"
              @click="deleteDocument(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </SectionCard>
        <SectionCard title="知识库检索测试">

    <el-space
        style="width:100%"
    >

        <el-input
        v-model="searchQuery"
        placeholder="输入一个问题..."
        clearable
        />

        <el-button
        type="primary"
        :loading="searching"
        @click="searchKnowledge"
        >

        检索

        </el-button>
    

        <EmptyState
        v-if="!searchResults.length"
        title="暂无检索结果"
        />

        <el-card
        v-for="item in searchResults"
        :key="item.id"
        shadow="never"
        >

        <h4>{{ item.title }}</h4>

        <p>{{ item.content }}</p>

        <el-tag>

            {{ item.score?.toFixed(3) }}

        </el-tag>

        </el-card>

    </el-space>

    </SectionCard>
      <!-- ========================= -->
    <!-- Upload Dialog -->
    <!-- ========================= -->
    <el-dialog
      v-model="showUploadDialog"
      title="上传知识文档"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form
        :model="uploadForm"
        label-width="90px"
      >
        <el-form-item label="标题">
          <el-input
            v-model="uploadForm.title"
            placeholder="留空则使用文件名"
          />
        </el-form-item>
        <el-form-item label="来源">
          <el-radio-group
            v-model="uploadForm.source_type"
          >
            <el-radio value="upload">
              用户上传
            </el-radio>
            <el-radio value="preset">
              系统预置
            </el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="文件">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            :show-file-list="true"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            accept=".pdf,.txt,.md"
          >
            <el-button type="primary">
              选择文件
            </el-button>
            <template #tip>
              <div class="upload-tip">
                支持 PDF、TXT、MD 文件
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button
          @click="showUploadDialog = false"
        >
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="uploading"
          @click="uploadDocument"
        >
          上传
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import request from "@/utils/request";

import {
  ElMessage,
  ElMessageBox,
} from "element-plus";

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
    ElMessage.error("获取知识文档失败");
    console.error(error);
  } finally{
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
      "确定构建预置知识库？",
      "提示",
      {
        type: "warning",
      }
    );
    const res = await request.post("/knowledge/build");
    ElMessage.success(res.message);
    fetchDocuments();
    fetchStats();
  } catch (error) {
    if (error !== "cancel") {
      ElMessage.error("构建失败");
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
    ElMessage.warning("请选择要上传的文件");
    return;
  }

  const formData = new FormData();

  formData.append("file", selectedFile.value);

  if (uploadForm.title.trim()) {
    formData.append("title", uploadForm.title.trim());
  }

  formData.append(
    "source_type",
    uploadForm.source_type
  );

  uploading.value = true;

  try {
    const res = await request.post(
      "/knowledge/upload",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );

    ElMessage.success(
      `上传成功，共生成 ${res.chunk_count} 个知识片段`
    );

    showUploadDialog.value = false;
    uploadForm.title = "";
    uploadForm.source_type = "upload";
    selectedFile.value = null;
    uploadRef.value?.clearFiles();
    await fetchDocuments();
    await fetchStats();
  } catch (error) {
    ElMessage.error(
      error.response?.data?.detail || "上传失败"
    );
  } finally {
    uploading.value = false;
  }
}

async function deleteDocument(row) {

  try {

    await ElMessageBox.confirm(
      `确定删除 "${row.title}"？`,
      "删除文档",
      {
        type: "warning",
      }
    );

    await request.delete(
      `/knowledge/documents/${row.id}`
    );
    ElMessage.success("删除成功");
    await fetchDocuments();
    await fetchStats();

  } catch (error) {
    if (error !== "cancel") {
      ElMessage.error("删除失败");
    }
  }
}
async function searchKnowledge() {
  if (!searchQuery.value.trim()) {
    ElMessage.warning("请输入检索内容");
    return;
  }
  searching.value = true;
  try {
    const res = await request.post(
      "/knowledge/search",
      {
        query: searchQuery.value,
        top_k: 5,
      }
    );
    searchResults.value = res.results || [];
  } catch (error) {
    ElMessage.error("检索失败");
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