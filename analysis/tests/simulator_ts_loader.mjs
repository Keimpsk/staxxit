// Node 24 strips erasable TypeScript natively. The simulator's bundler-style
// relative imports need only this extension resolver; source is not modified.
export async function resolve(specifier, context, nextResolve) {
  if ((specifier.startsWith('./') || specifier.startsWith('../')) &&
      !/\.[a-z0-9]+$/i.test(specifier)) {
    try {
      return await nextResolve(specifier + '.ts', context)
    } catch (error) {
      if (error.code !== 'ERR_MODULE_NOT_FOUND') throw error
    }
  }
  return nextResolve(specifier, context)
}
