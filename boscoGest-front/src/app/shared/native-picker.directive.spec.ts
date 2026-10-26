import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { NativePickerDirective } from './native-picker.directive';

@Component({
  imports: [MatFormFieldModule, MatInputModule, MatIconModule, NativePickerDirective],
  template: `
    <mat-form-field appearance="outline">
      <mat-label>Hora</mat-label>
      <input matInput type="time">
      <mat-icon matSuffix>schedule</mat-icon>
    </mat-form-field>
  `,
})
class HostComponent {}

describe('NativePickerDirective', () => {
  let input: HTMLInputElement;
  let host: HTMLElement;

  beforeEach(() => {
    const fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
    host = fixture.nativeElement;
    input = host.querySelector('input')!;
    spyOn(input, 'showPicker');
  });

  it('opens the picker when the icon is touched', () => {
    (host.querySelector('mat-icon') as HTMLElement).click();
    expect(input.showPicker).toHaveBeenCalled();
  });

  it('opens the picker when the box around the input is touched', () => {
    (host.querySelector('.mat-mdc-text-field-wrapper') as HTMLElement).click();
    expect(input.showPicker).toHaveBeenCalled();
  });

  it('leaves touches on the input itself to the browser', () => {
    input.click();
    expect(input.showPicker).not.toHaveBeenCalled();
  });

  it('does nothing when the field is disabled', () => {
    input.disabled = true;
    (host.querySelector('mat-icon') as HTMLElement).click();
    expect(input.showPicker).not.toHaveBeenCalled();
  });
});
