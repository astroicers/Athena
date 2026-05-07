<template>
  <div v-if="$slidev.nav.currentPage > 1" class="kiwis-footer">
    <span class="brand">@ 七維思 X 網路中文</span>
    <span class="page">{{ $slidev.nav.currentPage }} / {{ $slidev.nav.total }}</span>
  </div>
</template>
