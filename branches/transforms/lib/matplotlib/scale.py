import numpy as npy
from matplotlib.numerix import npyma as ma
MaskedArray = ma.MaskedArray

from ticker import NullFormatter, ScalarFormatter, LogFormatterMathtext
from ticker import NullLocator, LogLocator, AutoLocator, SymmetricalLogLocator
from transforms import Transform, IdentityTransform

class ScaleBase(object):
    def set_default_locators_and_formatters(self, axis):
        raise NotImplementedError

    def limit_range_for_scale(self, vmin, vmax, minpos):
        return vmin, vmax

class LinearScale(ScaleBase):
    name = 'linear'

    def __init__(self, axis, **kwargs):
        pass

    def set_default_locators_and_formatters(self, axis):
        axis.set_major_locator(AutoLocator())
        axis.set_major_formatter(ScalarFormatter())
        axis.set_minor_locator(NullLocator())
        axis.set_minor_formatter(NullFormatter())

    def get_transform(self):
        return IdentityTransform()

def _mask_non_positives(a):
    mask = a <= 0.0
    if mask.any():
        return ma.MaskedArray(a, mask=mask)
    return a

class LogScale(ScaleBase):
    name = 'log'

    class Log10Transform(Transform):
        input_dims = 1
        output_dims = 1
        is_separable = True
        base = 10.0

        def transform(self, a):
            a = _mask_non_positives(a * 10.0)
            if isinstance(a, MaskedArray):
                return ma.log10(a)
            return npy.log10(a)

        def inverted(self):
            return LogScale.InvertedLog10Transform()

    class InvertedLog10Transform(Transform):
        input_dims = 1
        output_dims = 1
        is_separable = True
        base = 10.0

        def transform(self, a):
            return ma.power(10.0, a) / 10.0

        def inverted(self):
            return LogScale.Log10Transform()

    class Log2Transform(Transform):
        input_dims = 1
        output_dims = 1
        is_separable = True
        base = 2.0

        def transform(self, a):
            a = _mask_non_positives(a * 2.0)
            if isinstance(a, MaskedArray):
                return ma.log2(a)
            return npy.log2(a)

        def inverted(self):
            return LogScale.InvertedLog2Transform()

    class InvertedLog2Transform(Transform):
        input_dims = 1
        output_dims = 1
        is_separable = True
        base = 2.0

        def transform(self, a):
            return ma.power(2.0, a) / 2.0

        def inverted(self):
            return LogScale.Log2Transform()

    class NaturalLogTransform(Transform):
        input_dims = 1
        output_dims = 1
        is_separable = True
        base = npy.e

        def transform(self, a):
            a = _mask_non_positives(a * npy.e)
            if isinstance(a, MaskedArray):
                return ma.log(a)
            return npy.log(a)

        def inverted(self):
            return LogScale.InvertedNaturalLogTransform()

    class InvertedNaturalLogTransform(Transform):
        input_dims = 1
        output_dims = 1
        is_separable = True
        base = npy.e

        def transform(self, a):
            return ma.power(npy.e, a) / npy.e

        def inverted(self):
            return LogScale.Log2Transform()

    class LogTransform(Transform):
        input_dims = 1
        output_dims = 1
        is_separable = True

        def __init__(self, base):
            Transform.__init__(self)
            self.base = base

        def transform(self, a):
            a = _mask_non_positives(a * self.base)
            if isinstance(a, MaskedArray):
                return ma.log(a) / npy.log(self.base)
            return npy.log(a) / npy.log(self.base)

        def inverted(self):
            return LogScale.InvertedLogTransform(self.base)

    class InvertedLogTransform(Transform):
        input_dims = 1
        output_dims = 1
        is_separable = True

        def __init__(self, base):
            Transform.__init__(self)
            self.base = base

        def transform(self, a):
            return ma.power(self.base, a) / self.base

        def inverted(self):
            return LogScale.LogTransform(self.base)


    def __init__(self, axis, **kwargs):
        if axis.axis_name == 'x':
            base = kwargs.pop('basex', 10.0)
            subs = kwargs.pop('subsx', None)
        else:
            base = kwargs.pop('basey', 10.0)
            subs = kwargs.pop('subsy', None)

        if base == 10.0:
            self._transform = self.Log10Transform()
        elif base == 2.0:
            self._transform = self.Log2Transform()
        elif base == npy.e:
            self._transform = self.NaturalLogTransform()
        else:
            self._transform = self.LogTransform(base)

        self.base = base
        self.subs = subs

    def set_default_locators_and_formatters(self, axis):
        axis.set_major_locator(LogLocator(self.base))
        axis.set_major_formatter(LogFormatterMathtext(self.base))
        axis.set_minor_locator(LogLocator(self.base, self.subs))
        axis.set_minor_formatter(NullFormatter())

    def get_transform(self):
        return self._transform

    def limit_range_for_scale(self, vmin, vmax, minpos):
        return (vmin <= 0.0 and minpos or vmin,
                vmax <= 0.0 and minpos or vmax)

class SymmetricalLogScale(ScaleBase):
    name = 'symlog'

    class SymmetricalLogTransform(Transform):
        input_dims = 1
        output_dims = 1
        is_separable = True

        def __init__(self, base, linthresh):
            Transform.__init__(self)
            self.base = base
            self.linthresh = linthresh
            self._log_base = npy.log(base)
            self._linadjust = (npy.log(linthresh) / self._log_base) / linthresh

        def transform(self, a):
            sign = npy.sign(npy.asarray(a))
            masked = ma.masked_inside(a, -self.linthresh, self.linthresh, copy=False)
            log = sign * ma.log(npy.abs(masked)) / self._log_base
            if masked.mask.any():
                return npy.asarray(ma.where(masked.mask,
                                            a * self._linadjust,
                                            log))
            else:
                return npy.asarray(log)

        def inverted(self):
            return SymmetricalLogScale.InvertedSymmetricalLogTransform(self.base, self.linthresh)

    class InvertedSymmetricalLogTransform(Transform):
        input_dims = 1
        output_dims = 1
        is_separable = True

        def __init__(self, base, linthresh):
            Transform.__init__(self)
            self.base = base
            self.linthresh = linthresh
            self._log_base = npy.log(base)
            self._log_linthresh = npy.log(linthresh) / self._log_base
            self._linadjust = linthresh / (npy.log(linthresh) / self._log_base)

        def transform(self, a):
            return npy.where(a <= self._log_linthresh,
                             npy.where(a >= -self._log_linthresh,
                                       a * self._linadjust,
                                       -(npy.power(self.base, -a))),
                             npy.power(self.base, a))

        def inverted(self):
            return SymmetricalLogScale.SymmetricalLogTransform(self.base)

    def __init__(self, axis, **kwargs):
        if axis.axis_name == 'x':
            base = kwargs.pop('basex', 10.0)
            linthresh = kwargs.pop('linthreshx', 2.0)
            subs = kwargs.pop('subsx', None)
        else:
            base = kwargs.pop('basey', 10.0)
            linthresh = kwargs.pop('linthreshy', 2.0)
            subs = kwargs.pop('subsy', None)

        self._transform = self.SymmetricalLogTransform(base, linthresh)

        self.base = base
        self.linthresh = linthresh
        self.subs = subs

    def set_default_locators_and_formatters(self, axis):
        axis.set_major_locator(SymmetricalLogLocator(self.get_transform()))
        axis.set_major_formatter(LogFormatterMathtext(self.base))
        axis.set_minor_locator(SymmetricalLogLocator(self.get_transform(), self.subs))
        axis.set_minor_formatter(NullFormatter())

    def get_transform(self):
        return self._transform


_scale_mapping = {
    'linear'    : LinearScale,
    'log'       : LogScale,
    'symlog'    : SymmetricalLogScale
    }
def scale_factory(scale, axis, **kwargs):
    scale = scale.lower()
    if scale is None:
        scale = 'linear'

    if not _scale_mapping.has_key(scale):
        raise ValueError("Unknown scale type '%s'" % scale)

    return _scale_mapping[scale](axis, **kwargs)

def get_scale_names():
    names = _scale_mapping.keys()
    names.sort()
    return names
